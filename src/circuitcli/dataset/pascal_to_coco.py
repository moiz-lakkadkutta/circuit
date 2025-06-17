"""Convert Pascal VOC XML annotations to COCO JSON format."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import hashlib
from PIL import Image
from rich.console import Console
from rich.progress import Progress, TaskID
import random

from .constants import ALL_COMPONENT_CLASSES, COCO_INFO, DATASET_CONFIG

console = Console()


class PascalToCOCOConverter:
    """Convert Pascal VOC format annotations to COCO JSON format."""
    
    def __init__(self, images_dir: Path, annotations_dir: Path):
        """Initialize the converter.
        
        Args:
            images_dir: Directory containing the images.
            annotations_dir: Directory containing Pascal VOC XML files.
        """
        self.images_dir = Path(images_dir)
        self.annotations_dir = Path(annotations_dir)
        self.coco_data = self._initialize_coco_structure()
        self.category_map = self._create_category_map()
        self.image_id_counter = 1
        self.annotation_id_counter = 1
        
    def _initialize_coco_structure(self) -> Dict[str, Any]:
        """Initialize the COCO JSON structure."""
        return {
            "info": {
                **COCO_INFO,
                "date_created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "licenses": [
                {
                    "id": 1,
                    "name": "Custom License",
                    "url": ""
                }
            ],
            "images": [],
            "annotations": [],
            "categories": []
        }
    
    def _create_category_map(self) -> Dict[str, int]:
        """Create mapping from category names to category IDs."""
        category_map = {}
        
        for idx, category_name in enumerate(ALL_COMPONENT_CLASSES, 1):
            category_info = {
                "id": idx,
                "name": category_name,
                "supercategory": "electrical_component"
            }
            self.coco_data["categories"].append(category_info)
            category_map[category_name] = idx
            
        return category_map
    
    def _get_image_info(self, image_path: Path) -> Tuple[int, int]:
        """Get image dimensions.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            Tuple of (width, height).
        """
        try:
            with Image.open(image_path) as img:
                return img.size
        except Exception as e:
            console.print(f"❌ Error reading image {image_path}: {e}")
            return (0, 0)
    
    def _parse_pascal_xml(self, xml_path: Path) -> List[Dict[str, Any]]:
        """Parse Pascal VOC XML file.
        
        Args:
            xml_path: Path to the XML annotation file.
            
        Returns:
            List of annotation dictionaries.
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            annotations = []
            
            for obj in root.findall('object'):
                # Get category name
                category_name = obj.find('name').text.lower().strip()
                
                # Skip if category not in our defined classes
                if category_name not in self.category_map:
                    console.print(f"⚠️  Unknown category '{category_name}' in {xml_path}")
                    continue
                
                # Get bounding box
                bndbox = obj.find('bndbox')
                xmin = int(float(bndbox.find('xmin').text))
                ymin = int(float(bndbox.find('ymin').text))
                xmax = int(float(bndbox.find('xmax').text))
                ymax = int(float(bndbox.find('ymax').text))
                
                # Calculate width and height
                width = xmax - xmin
                height = ymax - ymin
                area = width * height
                
                # Skip if bounding box is too small
                if area < DATASET_CONFIG["min_bbox_area"]:
                    continue
                
                # Get additional attributes
                difficult = obj.find('difficult')
                is_difficult = int(difficult.text) if difficult is not None else 0
                
                annotation = {
                    "category_name": category_name,
                    "bbox": [xmin, ymin, width, height],
                    "area": area,
                    "iscrowd": 0,
                    "difficult": is_difficult
                }
                
                annotations.append(annotation)
                
            return annotations
            
        except Exception as e:
            console.print(f"❌ Error parsing XML {xml_path}: {e}")
            return []
    
    def convert_single_image(self, image_path: Path) -> bool:
        """Convert a single image and its annotations.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            True if successful, False otherwise.
        """
        # Find corresponding XML file
        xml_path = self.annotations_dir / f"{image_path.stem}.xml"
        
        if not xml_path.exists():
            console.print(f"⚠️  No XML annotation found for {image_path.name}")
            return False
        
        # Get image dimensions
        width, height = self._get_image_info(image_path)
        if width == 0 or height == 0:
            return False
        
        # Add image info to COCO data
        image_info = {
            "id": self.image_id_counter,
            "width": width,
            "height": height,
            "file_name": image_path.name,
            "license": 1,
            "flickr_url": "",
            "coco_url": "",
            "date_captured": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.coco_data["images"].append(image_info)
        
        # Parse annotations
        annotations = self._parse_pascal_xml(xml_path)
        
        # Add annotations to COCO data
        for ann in annotations:
            annotation_info = {
                "id": self.annotation_id_counter,
                "image_id": self.image_id_counter,
                "category_id": self.category_map[ann["category_name"]],
                "segmentation": [],  # Empty for bounding box only
                "area": ann["area"],
                "bbox": ann["bbox"],
                "iscrowd": ann["iscrowd"]
            }
            
            self.coco_data["annotations"].append(annotation_info)
            self.annotation_id_counter += 1
        
        self.image_id_counter += 1
        return True
    
    def convert_dataset(self, output_path: Path) -> bool:
        """Convert the entire dataset.
        
        Args:
            output_path: Path to save the COCO JSON file.
            
        Returns:
            True if successful, False otherwise.
        """
        if not self.images_dir.exists():
            console.print(f"❌ Images directory does not exist: {self.images_dir}")
            return False
            
        if not self.annotations_dir.exists():
            console.print(f"❌ Annotations directory does not exist: {self.annotations_dir}")
            return False
        
        # Get all image files
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(self.images_dir.glob(f"*{ext}"))
            image_files.extend(self.images_dir.glob(f"*{ext.upper()}"))
        
        if not image_files:
            console.print(f"❌ No image files found in {self.images_dir}")
            return False
        
        console.print(f"📸 Found {len(image_files)} images to process")
        
        # Process images with progress bar
        with Progress(console=console) as progress:
            task = progress.add_task("Converting images...", total=len(image_files))
            
            successful_conversions = 0
            for image_path in image_files:
                if self.convert_single_image(image_path):
                    successful_conversions += 1
                progress.advance(task)
        
        # Save COCO JSON
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(self.coco_data, f, indent=2)
            
            console.print(f"✅ Successfully converted {successful_conversions}/{len(image_files)} images")
            console.print(f"📄 COCO JSON saved to: {output_path}")
            console.print(f"📊 Total images: {len(self.coco_data['images'])}")
            console.print(f"📊 Total annotations: {len(self.coco_data['annotations'])}")
            console.print(f"📊 Total categories: {len(self.coco_data['categories'])}")
            
            return True
            
        except Exception as e:
            console.print(f"❌ Error saving COCO JSON: {e}")
            return False


def create_train_val_test_splits(
    coco_json_path: Path,
    output_dir: Path,
    train_ratio: float = 0.7,
    val_ratio: float = 0.2,
    test_ratio: float = 0.1,
    random_seed: int = 42
) -> bool:
    """Create train/validation/test splits from COCO JSON.
    
    Args:
        coco_json_path: Path to the main COCO JSON file.
        output_dir: Directory to save the split files.
        train_ratio: Ratio for training set.
        val_ratio: Ratio for validation set.
        test_ratio: Ratio for test set.
        random_seed: Random seed for reproducible splits.
        
    Returns:
        True if successful, False otherwise.
    """
    try:
        # Load COCO data
        with open(coco_json_path, 'r') as f:
            coco_data = json.load(f)
        
        # Set random seed
        random.seed(random_seed)
        
        # Shuffle images
        images = coco_data['images'].copy()
        random.shuffle(images)
        
        # Calculate split indices
        total_images = len(images)
        train_end = int(total_images * train_ratio)
        val_end = train_end + int(total_images * val_ratio)
        
        # Create splits
        train_images = images[:train_end]
        val_images = images[train_end:val_end]
        test_images = images[val_end:]
        
        # Create image ID sets for filtering annotations
        train_image_ids = {img['id'] for img in train_images}
        val_image_ids = {img['id'] for img in val_images}
        test_image_ids = {img['id'] for img in test_images}
        
        # Filter annotations for each split
        train_annotations = [ann for ann in coco_data['annotations'] if ann['image_id'] in train_image_ids]
        val_annotations = [ann for ann in coco_data['annotations'] if ann['image_id'] in val_image_ids]
        test_annotations = [ann for ann in coco_data['annotations'] if ann['image_id'] in test_image_ids]
        
        # Create split datasets
        splits = {
            'train': {
                'images': train_images,
                'annotations': train_annotations
            },
            'val': {
                'images': val_images,
                'annotations': val_annotations
            },
            'test': {
                'images': test_images,
                'annotations': test_annotations
            }
        }
        
        # Save each split
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for split_name, split_data in splits.items():
            split_coco = {
                'info': coco_data['info'],
                'licenses': coco_data['licenses'],
                'categories': coco_data['categories'],
                'images': split_data['images'],
                'annotations': split_data['annotations']
            }
            
            output_path = output_dir / f"{split_name}.json"
            with open(output_path, 'w') as f:
                json.dump(split_coco, f, indent=2)
            
            console.print(f"✅ {split_name.capitalize()} split: {len(split_data['images'])} images, "
                         f"{len(split_data['annotations'])} annotations")
        
        console.print(f"📁 Split files saved to: {output_dir}")
        return True
        
    except Exception as e:
        console.print(f"❌ Error creating splits: {e}")
        return False 