"""OCR engine for extracting component values and labels."""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
import numpy as np
import cv2
from PIL import Image
import easyocr
from rich.console import Console
from rich.progress import Progress, track
import pandas as pd

console = Console()


class CircuitOCR:
    """OCR engine specialized for electrical circuit component text extraction."""
    
    def __init__(self, 
                 languages: List[str] = ['en'],
                 gpu: bool = True,
                 model_storage_directory: Optional[str] = None,
                 download_enabled: bool = True):
        """Initialize the CircuitOCR engine.
        
        Args:
            languages: List of language codes for OCR
            gpu: Whether to use GPU acceleration
            model_storage_directory: Directory to store OCR models
            download_enabled: Whether to allow model downloads
        """
        self.languages = languages
        self.gpu = gpu and self._is_gpu_available()
        
        try:
            # Initialize EasyOCR reader
            self.reader = easyocr.Reader(
                lang_list=languages,
                gpu=self.gpu,
                model_storage_directory=model_storage_directory,
                download_enabled=download_enabled
            )
            
            console.print(f"🔤 Initialized CircuitOCR:")
            console.print(f"   Languages: {languages}")
            console.print(f"   GPU: {self.gpu}")
            
        except Exception as e:
            console.print(f"❌ Error initializing OCR: {e}")
            raise
        
        # Component value patterns
        self.value_patterns = self._setup_value_patterns()
        
        # Component label patterns
        self.label_patterns = self._setup_label_patterns()
        
    def _is_gpu_available(self) -> bool:
        """Check if GPU is available for OCR."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def _setup_value_patterns(self) -> Dict[str, List[str]]:
        """Setup regex patterns for component values."""
        return {
            # Resistance values
            "resistance": [
                r'\b\d+(?:\.\d+)?\s*[kKmM]?[ΩΩohm]*\b',  # 10kΩ, 1.5MΩ, 470Ω
                r'\b\d+(?:\.\d+)?\s*[kKmM]?\s*[ΩΩ]\b',    # 10 kΩ, 1.5 MΩ
                r'\b\d+[kKmM]\d*\b',                       # 10k, 1M5 (common notation)
            ],
            
            # Capacitance values
            "capacitance": [
                r'\b\d+(?:\.\d+)?\s*[pnuμmM]?[Ff]\b',      # 100pF, 10nF, 1μF, 10mF
                r'\b\d+(?:\.\d+)?\s*[pnuμmM]?\s*[Ff]\b',   # 100 pF, 10 nF
                r'\b\d+[pnuμmM]\d*[Ff]?\b',                # 10n, 1u5
            ],
            
            # Inductance values
            "inductance": [
                r'\b\d+(?:\.\d+)?\s*[pnuμmM]?[Hh]\b',      # 100pH, 10nH, 1μH, 10mH
                r'\b\d+(?:\.\d+)?\s*[pnuμmM]?\s*[Hh]\b',   # 100 pH, 10 nH
            ],
            
            # Voltage values
            "voltage": [
                r'\b\d+(?:\.\d+)?\s*[mkK]?[Vv]\b',         # 5V, 3.3V, 12kV
                r'\b\d+(?:\.\d+)?\s*[mkK]?\s*[Vv]\b',      # 5 V, 3.3 V
            ],
            
            # Current values
            "current": [
                r'\b\d+(?:\.\d+)?\s*[pnuμmMA]?[Aa]\b',     # 10mA, 1A, 100μA
                r'\b\d+(?:\.\d+)?\s*[pnuμmMA]?\s*[Aa]\b',  # 10 mA, 1 A
            ],
            
            # Frequency values
            "frequency": [
                r'\b\d+(?:\.\d+)?\s*[kKmMgG]?[Hh][zZ]\b', # 1kHz, 10MHz, 1GHz
                r'\b\d+(?:\.\d+)?\s*[kKmMgG]?\s*[Hh][zZ]\b',
            ],
            
            # Power values
            "power": [
                r'\b\d+(?:\.\d+)?\s*[mkK]?[Ww]\b',         # 10W, 1.5kW, 100mW
                r'\b\d+(?:\.\d+)?\s*[mkK]?\s*[Ww]\b',
            ]
        }
    
    def _setup_label_patterns(self) -> Dict[str, List[str]]:
        """Setup regex patterns for component labels."""
        return {
            "resistor": [r'\b[Rr]\d+\b', r'\bR[A-Z]?\d+\b'],        # R1, R2, RA1
            "capacitor": [r'\b[Cc]\d+\b', r'\bC[A-Z]?\d+\b'],       # C1, C2, CA1
            "inductor": [r'\b[Ll]\d+\b', r'\bL[A-Z]?\d+\b'],        # L1, L2, LA1
            "diode": [r'\b[Dd]\d+\b', r'\bD[A-Z]?\d+\b'],           # D1, D2, DA1
            "transistor": [r'\b[QqTt]\d+\b', r'\b[QT][A-Z]?\d+\b'], # Q1, T1, QA1
            "opamp": [r'\b[Uu]\d+\b', r'\bU[A-Z]?\d+\b'],           # U1, U2, UA1
            "voltage_source": [r'\b[VvEe]\d+\b'],                   # V1, E1
            "current_source": [r'\b[Ii]\d+\b'],                     # I1, I2
            "switch": [r'\b[Ss][Ww]?\d+\b'],                        # S1, SW1
            "test_point": [r'\b[Tt][Pp]\d+\b'],                     # TP1, TP2
            "connector": [r'\b[JjPp]\d+\b'],                        # J1, P1
            "crystal": [r'\b[Xx][Tt][Aa][Ll]?\d+\b', r'\b[Yy]\d+\b'], # XTAL1, Y1
        }
    
    def preprocess_image(self, image: Union[Image.Image, np.ndarray]) -> np.ndarray:
        """Preprocess image for better OCR performance.
        
        Args:
            image: Input image (PIL Image or numpy array)
            
        Returns:
            Preprocessed image as numpy array
        """
        # Convert PIL to numpy if needed
        if isinstance(image, Image.Image):
            image = np.array(image)
        
        # Convert to grayscale if color
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        # Apply preprocessing steps
        processed = gray.copy()
        
        # 1. Denoise
        processed = cv2.medianBlur(processed, 3)
        
        # 2. Enhance contrast
        processed = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(processed)
        
        # 3. Threshold to binary
        _, processed = cv2.threshold(processed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 4. Morphological operations to clean up text
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel)
        
        return processed
    
    def extract_text(self, 
                    image: Union[Image.Image, np.ndarray],
                    preprocess: bool = True,
                    confidence_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Extract text from image using OCR.
        
        Args:
            image: Input image
            preprocess: Whether to preprocess image
            confidence_threshold: Minimum confidence for text detection
            
        Returns:
            List of detected text regions with metadata
        """
        try:
            # Preprocess if requested
            if preprocess:
                if isinstance(image, Image.Image):
                    image_array = self.preprocess_image(image)
                else:
                    image_array = self.preprocess_image(image)
            else:
                if isinstance(image, Image.Image):
                    image_array = np.array(image)
                else:
                    image_array = image
            
            # Run OCR
            results = self.reader.readtext(image_array)
            
            # Process results
            text_detections = []
            for (bbox, text, confidence) in results:
                if confidence >= confidence_threshold:
                    # Extract bounding box coordinates
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]
                    
                    x_min, x_max = min(x_coords), max(x_coords)
                    y_min, y_max = min(y_coords), max(y_coords)
                    
                    text_detections.append({
                        'text': text.strip(),
                        'confidence': confidence,
                        'bbox': [x_min, y_min, x_max - x_min, y_max - y_min],  # COCO format
                        'bbox_points': bbox
                    })
            
            return text_detections
            
        except Exception as e:
            console.print(f"❌ OCR extraction failed: {e}")
            return []
    
    def extract_component_values(self, text_detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract component values from detected text.
        
        Args:
            text_detections: List of text detections from OCR
            
        Returns:
            List of extracted component values with metadata
        """
        component_values = []
        
        for detection in text_detections:
            text = detection['text']
            
            # Try to match against each value pattern
            for value_type, patterns in self.value_patterns.items():
                for pattern in patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    
                    for match in matches:
                        # Parse the value
                        parsed_value = self._parse_component_value(match, value_type)
                        
                        if parsed_value:
                            component_values.append({
                                'original_text': text,
                                'matched_text': match,
                                'value_type': value_type,
                                'parsed_value': parsed_value,
                                'confidence': detection['confidence'],
                                'bbox': detection['bbox'],
                                'bbox_points': detection['bbox_points']
                            })
        
        return component_values
    
    def extract_component_labels(self, text_detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract component labels (designators) from detected text.
        
        Args:
            text_detections: List of text detections from OCR
            
        Returns:
            List of extracted component labels with metadata
        """
        component_labels = []
        
        for detection in text_detections:
            text = detection['text']
            
            # Try to match against each label pattern
            for component_type, patterns in self.label_patterns.items():
                for pattern in patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    
                    for match in matches:
                        component_labels.append({
                            'original_text': text,
                            'matched_text': match,
                            'component_type': component_type,
                            'designator': match.upper(),
                            'confidence': detection['confidence'],
                            'bbox': detection['bbox'],
                            'bbox_points': detection['bbox_points']
                        })
        
        return component_labels
    
    def _parse_component_value(self, value_text: str, value_type: str) -> Optional[Dict[str, Any]]:
        """Parse component value text into structured data.
        
        Args:
            value_text: Raw value text (e.g., "10kΩ", "100pF")
            value_type: Type of component value
            
        Returns:
            Parsed value dictionary or None if parsing fails
        """
        try:
            # Clean the text
            clean_text = value_text.strip().upper()
            
            # Extract numeric part and unit
            numeric_match = re.match(r'(\d+(?:\.\d+)?)', clean_text)
            if not numeric_match:
                return None
            
            base_value = float(numeric_match.group(1))
            
            # Determine multiplier based on prefix
            multipliers = {
                'P': 1e-12,  # pico
                'N': 1e-9,   # nano
                'U': 1e-6,   # micro (μ)
                'μ': 1e-6,   # micro
                'M': 1e-3,   # milli (for current/power) or mega (for resistance)
                'K': 1e3,    # kilo
                'G': 1e9     # giga
            }
            
            multiplier = 1.0
            unit = ""
            
            # Extract multiplier and unit
            if value_type == "resistance":
                if 'K' in clean_text:
                    multiplier = 1e3
                elif 'M' in clean_text:
                    multiplier = 1e6
                unit = "Ω"
                
            elif value_type == "capacitance":
                if 'P' in clean_text:
                    multiplier = 1e-12
                elif 'N' in clean_text:
                    multiplier = 1e-9
                elif 'U' in clean_text or 'μ' in clean_text:
                    multiplier = 1e-6
                elif 'M' in clean_text:
                    multiplier = 1e-3
                unit = "F"
                
            elif value_type == "inductance":
                if 'P' in clean_text:
                    multiplier = 1e-12
                elif 'N' in clean_text:
                    multiplier = 1e-9
                elif 'U' in clean_text or 'μ' in clean_text:
                    multiplier = 1e-6
                elif 'M' in clean_text:
                    multiplier = 1e-3
                unit = "H"
                
            elif value_type in ["voltage", "current", "power"]:
                if 'M' in clean_text:
                    multiplier = 1e-3
                elif 'K' in clean_text:
                    multiplier = 1e3
                
                if value_type == "voltage":
                    unit = "V"
                elif value_type == "current":
                    unit = "A"
                elif value_type == "power":
                    unit = "W"
                    
            elif value_type == "frequency":
                if 'K' in clean_text:
                    multiplier = 1e3
                elif 'M' in clean_text:
                    multiplier = 1e6
                elif 'G' in clean_text:
                    multiplier = 1e9
                unit = "Hz"
            
            # Calculate final value
            final_value = base_value * multiplier
            
            return {
                'value': final_value,
                'base_value': base_value,
                'multiplier': multiplier,
                'unit': unit,
                'formatted': f"{base_value}{self._get_prefix_symbol(multiplier)}{unit}",
                'engineering_notation': self._to_engineering_notation(final_value, unit)
            }
            
        except Exception as e:
            console.print(f"⚠️  Error parsing value '{value_text}': {e}")
            return None
    
    def _get_prefix_symbol(self, multiplier: float) -> str:
        """Get SI prefix symbol for multiplier."""
        prefix_map = {
            1e-12: 'p',
            1e-9: 'n',
            1e-6: 'μ',
            1e-3: 'm',
            1.0: '',
            1e3: 'k',
            1e6: 'M',
            1e9: 'G'
        }
        return prefix_map.get(multiplier, '')
    
    def _to_engineering_notation(self, value: float, unit: str) -> str:
        """Convert value to engineering notation."""
        if value == 0:
            return f"0 {unit}"
        
        # Find appropriate prefix
        prefixes = [(1e9, 'G'), (1e6, 'M'), (1e3, 'k'), (1.0, ''), 
                   (1e-3, 'm'), (1e-6, 'μ'), (1e-9, 'n'), (1e-12, 'p')]
        
        for multiplier, prefix in prefixes:
            if abs(value) >= multiplier:
                scaled_value = value / multiplier
                # Format to remove unnecessary decimals
                if scaled_value == int(scaled_value):
                    return f"{int(scaled_value)}{prefix}{unit}"
                else:
                    return f"{scaled_value:.2f}{prefix}{unit}".rstrip('0').rstrip('.')
        
        # Fallback for very small values
        return f"{value:.2e} {unit}"
    
    def process_circuit_image(self, 
                            image: Union[Image.Image, np.ndarray],
                            confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """Process a complete circuit image and extract all text information.
        
        Args:
            image: Circuit image
            confidence_threshold: Minimum confidence for text detection
            
        Returns:
            Dictionary containing all extracted information
        """
        console.print("🔤 Processing circuit image with OCR...")
        
        # Extract all text
        text_detections = self.extract_text(image, preprocess=True, 
                                          confidence_threshold=confidence_threshold)
        
        # Extract component values
        component_values = self.extract_component_values(text_detections)
        
        # Extract component labels
        component_labels = self.extract_component_labels(text_detections)
        
        results = {
            'text_detections': text_detections,
            'component_values': component_values,
            'component_labels': component_labels,
            'summary': {
                'total_text_regions': len(text_detections),
                'component_values_found': len(component_values),
                'component_labels_found': len(component_labels),
                'value_types': list(set([v['value_type'] for v in component_values])),
                'component_types': list(set([l['component_type'] for l in component_labels]))
            }
        }
        
        console.print(f"✅ OCR processing completed:")
        console.print(f"   Text regions: {results['summary']['total_text_regions']}")
        console.print(f"   Component values: {results['summary']['component_values_found']}")
        console.print(f"   Component labels: {results['summary']['component_labels_found']}")
        
        return results
    
    def batch_process_images(self, 
                           image_paths: List[Path],
                           output_dir: Optional[Path] = None,
                           confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """Process multiple circuit images in batch.
        
        Args:
            image_paths: List of image file paths
            output_dir: Directory to save results (optional)
            confidence_threshold: Minimum confidence for text detection
            
        Returns:
            Batch processing results
        """
        console.print(f"🔤 Batch processing {len(image_paths)} images...")
        
        batch_results = {}
        all_values = []
        all_labels = []
        
        with Progress() as progress:
            task = progress.add_task("Processing images...", total=len(image_paths))
            
            for image_path in image_paths:
                try:
                    # Open image
                    image = Image.open(image_path)
                    
                    # Process image
                    results = self.process_circuit_image(image, confidence_threshold)
                    
                    # Store results
                    batch_results[str(image_path)] = results
                    all_values.extend(results['component_values'])
                    all_labels.extend(results['component_labels'])
                    
                except Exception as e:
                    console.print(f"❌ Error processing {image_path}: {e}")
                    batch_results[str(image_path)] = {'error': str(e)}
                
                progress.advance(task)
        
        # Create summary
        batch_summary = {
            'total_images': len(image_paths),
            'successful_images': len([r for r in batch_results.values() if 'error' not in r]),
            'failed_images': len([r for r in batch_results.values() if 'error' in r]),
            'total_values': len(all_values),
            'total_labels': len(all_labels),
            'value_types_distribution': self._get_value_type_distribution(all_values),
            'component_types_distribution': self._get_component_type_distribution(all_labels)
        }
        
        # Save results if output directory specified
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save detailed results as JSON
            import json
            with open(output_dir / 'ocr_results.json', 'w') as f:
                # Convert numpy arrays to lists for JSON serialization
                json_results = self._prepare_for_json(batch_results)
                json.dump(json_results, f, indent=2)
            
            # Save summary as CSV
            self._save_summary_csv(batch_summary, all_values, all_labels, output_dir)
        
        console.print(f"✅ Batch processing completed:")
        console.print(f"   Successful: {batch_summary['successful_images']}/{batch_summary['total_images']}")
        console.print(f"   Total values: {batch_summary['total_values']}")
        console.print(f"   Total labels: {batch_summary['total_labels']}")
        
        return {
            'results': batch_results,
            'summary': batch_summary
        }
    
    def _get_value_type_distribution(self, values: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get distribution of value types."""
        distribution = {}
        for value in values:
            value_type = value['value_type']
            distribution[value_type] = distribution.get(value_type, 0) + 1
        return distribution
    
    def _get_component_type_distribution(self, labels: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get distribution of component types."""
        distribution = {}
        for label in labels:
            component_type = label['component_type']
            distribution[component_type] = distribution.get(component_type, 0) + 1
        return distribution
    
    def _prepare_for_json(self, data: Any) -> Any:
        """Prepare data for JSON serialization by converting numpy arrays."""
        if isinstance(data, dict):
            return {key: self._prepare_for_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._prepare_for_json(item) for item in data]
        elif isinstance(data, np.ndarray):
            return data.tolist()
        elif isinstance(data, np.integer):
            return int(data)
        elif isinstance(data, np.floating):
            return float(data)
        else:
            return data
    
    def _save_summary_csv(self, 
                         batch_summary: Dict[str, Any],
                         all_values: List[Dict[str, Any]],
                         all_labels: List[Dict[str, Any]],
                         output_dir: Path):
        """Save summary statistics as CSV files."""
        try:
            # Values summary
            if all_values:
                values_df = pd.DataFrame(all_values)
                values_df.to_csv(output_dir / 'component_values.csv', index=False)
            
            # Labels summary
            if all_labels:
                labels_df = pd.DataFrame(all_labels)
                labels_df.to_csv(output_dir / 'component_labels.csv', index=False)
            
            # Overall summary
            summary_data = {
                'metric': list(batch_summary.keys()),
                'value': list(batch_summary.values())
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_csv(output_dir / 'batch_summary.csv', index=False)
            
        except Exception as e:
            console.print(f"⚠️  Warning: Failed to save CSV files: {e}")
    
    def evaluate_ocr_accuracy(self, 
                            ground_truth_file: Path,
                            predictions: Dict[str, Any]) -> Dict[str, float]:
        """Evaluate OCR accuracy against ground truth.
        
        Args:
            ground_truth_file: JSON file with ground truth annotations
            predictions: OCR predictions to evaluate
            
        Returns:
            Evaluation metrics
        """
        try:
            import json
            from difflib import SequenceMatcher
            
            # Load ground truth
            with open(ground_truth_file, 'r') as f:
                ground_truth = json.load(f)
            
            total_text_accuracy = []
            value_matches = 0
            total_values = 0
            label_matches = 0
            total_labels = 0
            
            for image_name, gt_data in ground_truth.items():
                if image_name in predictions:
                    pred_data = predictions[image_name]
                    
                    # Text accuracy (character-level)
                    for gt_text in gt_data.get('texts', []):
                        best_match = 0
                        for pred_text in pred_data.get('text_detections', []):
                            similarity = SequenceMatcher(None, gt_text.lower(), 
                                                       pred_text['text'].lower()).ratio()
                            best_match = max(best_match, similarity)
                        total_text_accuracy.append(best_match)
                    
                    # Value matching
                    gt_values = set(gt_data.get('values', []))
                    pred_values = set([v['matched_text'] for v in pred_data.get('component_values', [])])
                    
                    value_matches += len(gt_values.intersection(pred_values))
                    total_values += len(gt_values)
                    
                    # Label matching
                    gt_labels = set(gt_data.get('labels', []))
                    pred_labels = set([l['designator'] for l in pred_data.get('component_labels', [])])
                    
                    label_matches += len(gt_labels.intersection(pred_labels))
                    total_labels += len(gt_labels)
            
            # Calculate metrics
            metrics = {
                'text_accuracy': np.mean(total_text_accuracy) * 100 if total_text_accuracy else 0,
                'value_accuracy': (value_matches / total_values * 100) if total_values > 0 else 0,
                'label_accuracy': (label_matches / total_labels * 100) if total_labels > 0 else 0,
                'overall_accuracy': np.mean([
                    np.mean(total_text_accuracy) if total_text_accuracy else 0,
                    (value_matches / total_values) if total_values > 0 else 0,
                    (label_matches / total_labels) if total_labels > 0 else 0
                ]) * 100
            }
            
            console.print("📊 OCR Evaluation Results:")
            for metric, value in metrics.items():
                console.print(f"   {metric}: {value:.2f}%")
            
            return metrics
            
        except Exception as e:
            console.print(f"❌ OCR evaluation failed: {e}")
            return {} 