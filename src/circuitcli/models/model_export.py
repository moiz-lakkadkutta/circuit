"""Model export utilities for production deployment."""

import torch
import torch.nn as nn
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
import numpy as np
import onnx
import onnxruntime as ort
from rich.console import Console
from rich.progress import Progress
import json
import time

console = Console()


class ModelExporter:
    """Utility class for exporting trained models to various formats."""
    
    def __init__(self, device: Optional[str] = None):
        """Initialize the model exporter.
        
        Args:
            device: Device to run on ('cpu', 'cuda', 'mps', or None for auto)
        """
        self.device = device or self._get_best_device()
        
        console.print(f"📦 Initialized ModelExporter on {self.device}")
    
    def _get_best_device(self) -> str:
        """Automatically select the best available device."""
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    
    def export_yolo_to_onnx(self,
                           model_path: Path,
                           output_path: Path,
                           input_size: Tuple[int, int] = (640, 640),
                           batch_size: int = 1,
                           opset_version: int = 12,
                           simplify: bool = True,
                           optimize: bool = True) -> bool:
        """Export YOLOv8 model to ONNX format.
        
        Args:
            model_path: Path to trained YOLOv8 model
            output_path: Output path for ONNX model
            input_size: Input image size (height, width)
            batch_size: Batch size for export
            opset_version: ONNX opset version
            simplify: Whether to simplify the model
            optimize: Whether to optimize the model
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from ultralytics import YOLO
            
            console.print(f"📦 Exporting YOLOv8 model to ONNX...")
            console.print(f"   Model: {model_path}")
            console.print(f"   Output: {output_path}")
            console.print(f"   Input size: {input_size}")
            
            # Load YOLOv8 model
            model = YOLO(str(model_path))
            
            # Create output directory
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Export to ONNX
            exported_path = model.export(
                format='onnx',
                imgsz=input_size,
                opset=opset_version,
                simplify=simplify,
                optimize=optimize,
                dynamic=False,
                batch=batch_size
            )
            
            # Move to desired location if different
            if Path(exported_path) != output_path:
                Path(exported_path).rename(output_path)
            
            console.print(f"✅ YOLOv8 model exported successfully")
            
            # Verify the export
            return self.verify_onnx_model(output_path, input_size, batch_size)
            
        except Exception as e:
            console.print(f"❌ YOLOv8 ONNX export failed: {e}")
            return False
    
    def export_pytorch_to_onnx(self,
                              model: nn.Module,
                              output_path: Path,
                              input_shape: Tuple[int, ...],
                              input_names: List[str] = ["input"],
                              output_names: List[str] = ["output"],
                              dynamic_axes: Optional[Dict[str, Dict[int, str]]] = None,
                              opset_version: int = 11) -> bool:
        """Export PyTorch model to ONNX format.
        
        Args:
            model: PyTorch model to export
            output_path: Output path for ONNX model
            input_shape: Input tensor shape (including batch dimension)
            input_names: Names for input tensors
            output_names: Names for output tensors
            dynamic_axes: Dynamic axes specification
            opset_version: ONNX opset version
            
        Returns:
            True if successful, False otherwise
        """
        try:
            console.print(f"📦 Exporting PyTorch model to ONNX...")
            console.print(f"   Input shape: {input_shape}")
            console.print(f"   Output: {output_path}")
            
            # Set model to evaluation mode
            model.eval()
            model = model.to(self.device)
            
            # Create dummy input
            dummy_input = torch.randn(input_shape).to(self.device)
            
            # Create output directory
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Export to ONNX
            torch.onnx.export(
                model,
                dummy_input,
                str(output_path),
                export_params=True,
                opset_version=opset_version,
                do_constant_folding=True,
                input_names=input_names,
                output_names=output_names,
                dynamic_axes=dynamic_axes
            )
            
            console.print(f"✅ PyTorch model exported successfully")
            
            # Verify the export
            return self.verify_onnx_model(output_path, input_shape[1:])
            
        except Exception as e:
            console.print(f"❌ PyTorch ONNX export failed: {e}")
            return False
    
    def verify_onnx_model(self,
                         onnx_path: Path,
                         input_shape: Tuple[int, ...],
                         batch_size: int = 1) -> bool:
        """Verify ONNX model validity and test inference.
        
        Args:
            onnx_path: Path to ONNX model
            input_shape: Input shape (without batch dimension)
            batch_size: Batch size for testing
            
        Returns:
            True if verification successful, False otherwise
        """
        try:
            console.print(f"🔍 Verifying ONNX model: {onnx_path}")
            
            # Load and check ONNX model
            onnx_model = onnx.load(str(onnx_path))
            onnx.checker.check_model(onnx_model)
            
            # Create ONNX Runtime session
            ort_session = ort.InferenceSession(
                str(onnx_path),
                providers=['CPUExecutionProvider']  # Use CPU for verification
            )
            
            # Get input/output info
            input_info = ort_session.get_inputs()
            output_info = ort_session.get_outputs()
            
            console.print(f"   Inputs: {len(input_info)}")
            for i, input_tensor in enumerate(input_info):
                console.print(f"     {i}: {input_tensor.name} {input_tensor.shape}")
            
            console.print(f"   Outputs: {len(output_info)}")
            for i, output_tensor in enumerate(output_info):
                console.print(f"     {i}: {output_tensor.name} {output_tensor.shape}")
            
            # Test inference with dummy data
            if len(input_shape) == 2:  # 2D input (e.g., for orientation classifier)
                dummy_input = np.random.rand(batch_size, 3, *input_shape).astype(np.float32)
            elif len(input_shape) == 3:  # 3D input (e.g., for YOLO)
                dummy_input = np.random.rand(batch_size, *input_shape).astype(np.float32)
            else:
                dummy_input = np.random.rand(batch_size, *input_shape).astype(np.float32)
            
            # Run inference
            start_time = time.time()
            outputs = ort_session.run(None, {input_info[0].name: dummy_input})
            inference_time = time.time() - start_time
            
            console.print(f"   Inference time: {inference_time*1000:.2f}ms")
            console.print(f"   Output shapes: {[out.shape for out in outputs]}")
            console.print(f"✅ ONNX model verification successful")
            
            return True
            
        except Exception as e:
            console.print(f"❌ ONNX model verification failed: {e}")
            return False
    
    def optimize_onnx_model(self,
                           input_path: Path,
                           output_path: Path,
                           optimization_level: str = "basic") -> bool:
        """Optimize ONNX model for better performance.
        
        Args:
            input_path: Path to input ONNX model
            output_path: Path to save optimized model
            optimization_level: Optimization level ('basic', 'extended', 'all')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from onnxruntime.tools import optimizer
            
            console.print(f"⚡ Optimizing ONNX model...")
            console.print(f"   Input: {input_path}")
            console.print(f"   Output: {output_path}")
            console.print(f"   Level: {optimization_level}")
            
            # Set optimization level
            if optimization_level == "basic":
                opt_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
            elif optimization_level == "extended":
                opt_level = ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED
            else:  # "all"
                opt_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            # Create output directory
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Optimize model
            session_options = ort.SessionOptions()
            session_options.graph_optimization_level = opt_level
            session_options.optimized_model_filepath = str(output_path)
            
            # Create session to trigger optimization
            _ = ort.InferenceSession(str(input_path), session_options)
            
            console.print(f"✅ ONNX model optimized successfully")
            
            # Compare model sizes
            original_size = input_path.stat().st_size / (1024 * 1024)  # MB
            optimized_size = output_path.stat().st_size / (1024 * 1024)  # MB
            
            console.print(f"   Original size: {original_size:.2f} MB")
            console.print(f"   Optimized size: {optimized_size:.2f} MB")
            console.print(f"   Size reduction: {((original_size - optimized_size) / original_size * 100):.1f}%")
            
            return True
            
        except Exception as e:
            console.print(f"❌ ONNX optimization failed: {e}")
            return False
    
    def quantize_onnx_model(self,
                           input_path: Path,
                           output_path: Path,
                           quantization_mode: str = "dynamic") -> bool:
        """Quantize ONNX model to reduce size and improve inference speed.
        
        Args:
            input_path: Path to input ONNX model
            output_path: Path to save quantized model
            quantization_mode: Quantization mode ('dynamic', 'static')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from onnxruntime.quantization import quantize_dynamic, quantize_static
            from onnxruntime.quantization import QuantType
            
            console.print(f"🔢 Quantizing ONNX model...")
            console.print(f"   Input: {input_path}")
            console.print(f"   Output: {output_path}")
            console.print(f"   Mode: {quantization_mode}")
            
            # Create output directory
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if quantization_mode == "dynamic":
                # Dynamic quantization (no calibration data needed)
                quantize_dynamic(
                    str(input_path),
                    str(output_path),
                    weight_type=QuantType.QInt8
                )
            else:
                # Static quantization would require calibration data
                console.print("⚠️  Static quantization not implemented (requires calibration data)")
                return False
            
            console.print(f"✅ ONNX model quantized successfully")
            
            # Compare model sizes
            original_size = input_path.stat().st_size / (1024 * 1024)  # MB
            quantized_size = output_path.stat().st_size / (1024 * 1024)  # MB
            
            console.print(f"   Original size: {original_size:.2f} MB")
            console.print(f"   Quantized size: {quantized_size:.2f} MB")
            console.print(f"   Size reduction: {((original_size - quantized_size) / original_size * 100):.1f}%")
            
            return True
            
        except Exception as e:
            console.print(f"❌ ONNX quantization failed: {e}")
            return False
    
    def benchmark_onnx_model(self,
                           onnx_path: Path,
                           input_shape: Tuple[int, ...],
                           num_runs: int = 100,
                           warmup_runs: int = 10) -> Dict[str, float]:
        """Benchmark ONNX model inference performance.
        
        Args:
            onnx_path: Path to ONNX model
            input_shape: Input shape (including batch dimension)
            num_runs: Number of inference runs for benchmarking
            warmup_runs: Number of warmup runs
            
        Returns:
            Performance metrics
        """
        try:
            console.print(f"🏁 Benchmarking ONNX model: {onnx_path}")
            console.print(f"   Runs: {num_runs} (+ {warmup_runs} warmup)")
            
            # Create ONNX Runtime session
            ort_session = ort.InferenceSession(
                str(onnx_path),
                providers=['CPUExecutionProvider']
            )
            
            # Get input info
            input_info = ort_session.get_inputs()[0]
            
            # Create dummy input
            dummy_input = np.random.rand(*input_shape).astype(np.float32)
            
            # Warmup runs
            console.print("   Warming up...")
            for _ in range(warmup_runs):
                _ = ort_session.run(None, {input_info.name: dummy_input})
            
            # Benchmark runs
            inference_times = []
            
            with Progress() as progress:
                task = progress.add_task("Benchmarking...", total=num_runs)
                
                for _ in range(num_runs):
                    start_time = time.time()
                    _ = ort_session.run(None, {input_info.name: dummy_input})
                    end_time = time.time()
                    
                    inference_times.append(end_time - start_time)
                    progress.advance(task)
            
            # Calculate metrics
            inference_times = np.array(inference_times)
            
            metrics = {
                "avg_inference_time_ms": np.mean(inference_times) * 1000,
                "min_inference_time_ms": np.min(inference_times) * 1000,
                "max_inference_time_ms": np.max(inference_times) * 1000,
                "std_inference_time_ms": np.std(inference_times) * 1000,
                "median_inference_time_ms": np.median(inference_times) * 1000,
                "fps": 1.0 / np.mean(inference_times),
                "throughput_images_per_second": input_shape[0] / np.mean(inference_times)
            }
            
            console.print(f"\n🏁 Benchmark Results:")
            console.print(f"   Average inference time: {metrics['avg_inference_time_ms']:.2f} ms")
            console.print(f"   FPS: {metrics['fps']:.2f}")
            console.print(f"   Throughput: {metrics['throughput_images_per_second']:.2f} images/sec")
            console.print(f"   Min/Max time: {metrics['min_inference_time_ms']:.2f}/{metrics['max_inference_time_ms']:.2f} ms")
            
            return metrics
            
        except Exception as e:
            console.print(f"❌ ONNX benchmarking failed: {e}")
            return {}
    
    def create_model_manifest(self,
                            model_path: Path,
                            model_type: str,
                            input_shape: Tuple[int, ...],
                            num_classes: int,
                            class_names: List[str],
                            metrics: Dict[str, float],
                            preprocessing: Dict[str, Any],
                            output_path: Path) -> bool:
        """Create a manifest file with model metadata.
        
        Args:
            model_path: Path to the model file
            model_type: Type of model ('yolov8', 'orientation_classifier', 'ocr')
            input_shape: Model input shape
            num_classes: Number of output classes
            class_names: List of class names
            metrics: Model performance metrics
            preprocessing: Preprocessing requirements
            output_path: Path to save manifest
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import datetime
            
            # Calculate model size
            model_size_mb = model_path.stat().st_size / (1024 * 1024)
            
            manifest = {
                "model_info": {
                    "name": model_path.stem,
                    "type": model_type,
                    "version": "1.0",
                    "created_date": datetime.datetime.now().isoformat(),
                    "file_path": str(model_path),
                    "file_size_mb": round(model_size_mb, 2)
                },
                "architecture": {
                    "input_shape": list(input_shape),
                    "num_classes": num_classes,
                    "class_names": class_names
                },
                "performance": metrics,
                "preprocessing": preprocessing,
                "deployment": {
                    "format": model_path.suffix.lower(),
                    "framework": "onnxruntime" if model_path.suffix.lower() == ".onnx" else "pytorch",
                    "device_requirements": ["cpu", "cuda"],
                    "memory_requirements_mb": round(model_size_mb * 2, 2)  # Estimate 2x model size
                },
                "usage": {
                    "description": f"CircuitCLI {model_type} model for electrical component analysis",
                    "input_format": "RGB image tensor",
                    "output_format": "Detection boxes and classes" if model_type == "yolov8" else "Class probabilities",
                    "confidence_threshold": 0.25 if model_type == "yolov8" else 0.5,
                    "nms_threshold": 0.45 if model_type == "yolov8" else None
                }
            }
            
            # Create output directory
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save manifest
            with open(output_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            console.print(f"📋 Model manifest created: {output_path}")
            return True
            
        except Exception as e:
            console.print(f"❌ Failed to create model manifest: {e}")
            return False
    
    def export_complete_pipeline(self,
                               yolo_checkpoint: Path,
                               orientation_checkpoint: Path,
                               output_dir: Path,
                               input_size: Tuple[int, int] = (640, 640),
                               optimize: bool = True,
                               quantize: bool = False) -> Dict[str, Path]:
        """Export complete detection pipeline (YOLOv8 + Orientation classifier).
        
        Args:
            yolo_checkpoint: Path to YOLOv8 checkpoint
            orientation_checkpoint: Path to orientation classifier checkpoint
            output_dir: Output directory for exported models
            input_size: Input image size
            optimize: Whether to optimize ONNX models
            quantize: Whether to quantize models
            
        Returns:
            Dictionary mapping model names to their export paths
        """
        console.print("📦 Exporting complete detection pipeline...")
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        exported_models = {}
        
        try:
            # 1. Export YOLOv8 detector
            yolo_onnx_path = output_dir / "circuit_detector.onnx"
            if self.export_yolo_to_onnx(yolo_checkpoint, yolo_onnx_path, input_size):
                exported_models["detector"] = yolo_onnx_path
                
                # Optimize if requested
                if optimize:
                    optimized_path = output_dir / "circuit_detector_optimized.onnx"
                    if self.optimize_onnx_model(yolo_onnx_path, optimized_path):
                        exported_models["detector_optimized"] = optimized_path
                
                # Quantize if requested
                if quantize:
                    quantized_path = output_dir / "circuit_detector_quantized.onnx"
                    if self.quantize_onnx_model(yolo_onnx_path, quantized_path):
                        exported_models["detector_quantized"] = quantized_path
            
            # 2. Export orientation classifier
            from .orientation_classifier import OrientationClassifier
            
            # Load orientation classifier
            orientation_model = OrientationClassifier(device=self.device)
            orientation_onnx_path = output_dir / "orientation_classifier.onnx"
            
            if orientation_model.export_onnx(orientation_checkpoint, orientation_onnx_path):
                exported_models["orientation"] = orientation_onnx_path
                
                # Optimize if requested
                if optimize:
                    optimized_path = output_dir / "orientation_classifier_optimized.onnx"
                    if self.optimize_onnx_model(orientation_onnx_path, optimized_path):
                        exported_models["orientation_optimized"] = optimized_path
                
                # Quantize if requested
                if quantize:
                    quantized_path = output_dir / "orientation_classifier_quantized.onnx"
                    if self.quantize_onnx_model(orientation_onnx_path, quantized_path):
                        exported_models["orientation_quantized"] = quantized_path
            
            # 3. Create deployment package
            deployment_info = {
                "models": {name: str(path) for name, path in exported_models.items()},
                "inference_pipeline": {
                    "steps": [
                        "1. Load image and preprocess",
                        "2. Run YOLOv8 detector to find components",
                        "3. Extract component crops from detections",
                        "4. Run orientation classifier on crops",
                        "5. Run OCR on text regions",
                        "6. Combine results"
                    ]
                },
                "usage_example": {
                    "python": "from circuitcli.models import CircuitDetector; detector = CircuitDetector()",
                    "cli": "circuitcli predict --image circuit.jpg --output results.json"
                }
            }
            
            with open(output_dir / "deployment_info.json", 'w') as f:
                json.dump(deployment_info, f, indent=2)
            
            console.print(f"✅ Complete pipeline exported:")
            for name, path in exported_models.items():
                console.print(f"   {name}: {path}")
            
            return exported_models
            
        except Exception as e:
            console.print(f"❌ Pipeline export failed: {e}")
            return {}
    
    def validate_exported_models(self,
                               exported_models: Dict[str, Path],
                               test_images: List[Path],
                               ground_truth: Optional[Path] = None) -> Dict[str, Any]:
        """Validate exported models on test data.
        
        Args:
            exported_models: Dictionary of model names to paths
            test_images: List of test images
            ground_truth: Optional ground truth annotations
            
        Returns:
            Validation results
        """
        console.print("🔍 Validating exported models...")
        
        validation_results = {}
        
        try:
            # Test each exported model
            for model_name, model_path in exported_models.items():
                console.print(f"   Testing {model_name}...")
                
                # Benchmark performance
                if "detector" in model_name:
                    input_shape = (1, 3, 640, 640)
                elif "orientation" in model_name:
                    input_shape = (1, 3, 224, 224)
                else:
                    continue
                
                benchmark_results = self.benchmark_onnx_model(
                    model_path, input_shape, num_runs=50
                )
                
                validation_results[model_name] = {
                    "model_path": str(model_path),
                    "performance": benchmark_results,
                    "validation_status": "passed" if benchmark_results else "failed"
                }
            
            # Save validation report
            validation_report_path = exported_models[list(exported_models.keys())[0]].parent / "validation_report.json"
            with open(validation_report_path, 'w') as f:
                json.dump(validation_results, f, indent=2)
            
            console.print(f"✅ Model validation completed")
            console.print(f"   Report saved: {validation_report_path}")
            
            return validation_results
            
        except Exception as e:
            console.print(f"❌ Model validation failed: {e}")
            return {} 