"""Convert COCO format to YOLOv8 format."""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Any, Tuple
from rich.console import Console
from rich.progress import Progress, track

console = Console()


class COCOToYOLOConverter:
    """Convert COCO format dataset to YOLOv8 format."""
    
    def __init__(self):
        """Initialize the converter."""
        self.class_map = {}
        
    def convert_coco_to_yolo(self,
                           coco_json: Path,
                           images_dir: Path,
                           output_dir: Path,
                           split_name: str = "train") -> bool:
        """Convert COCO JSON to YOLOv8 format.
        
        Args:
            coco_json: Path to COCO JSON file
            images_dir: Directory containing images
            output_dir: Output directory for YOLOv8 format
            split_name: Name of the split (train/val/test)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            console.print(f"🔄 Converting {split_name} split from COCO to YOLOv8 format...")
            
            # Load COCO data
            with open(coco_json, 'r') as f:
                coco_data = json.load(f)
            
            # Create output directories
            yolo_images_dir = output_dir / "images" / split_name
            yolo_labels_dir = output_dir / "labels" / split_name
            
            yolo_images_dir.mkdir(parents=True, exist_ok=True)
            yolo_labels_dir.mkdir(parents=True, exist_ok=True)
            
            # Create class mapping
            self.class_map = {cat['id']: idx for idx, cat in enumerate(coco_data['categories'])}
            
            # Create image ID to annotations mapping
            image_annotations = {}
            for ann in coco_data['annotations']:
                image_id = ann['image_id']
                if image_id not in image_annotations:
                    image_annotations[image_id] = []
                image_annotations[image_id].append(ann)
            
            # Process each image
            processed_count = 0
            
            for image_info in track(coco_data['images'], description="Converting images..."):
                image_id = image_info['id']
                image_filename = image_info['file_name']
                image_width = image_info['width']
                image_height = image_info['height']
                
                # Find source image
                source_image_path = images_dir / image_filename
                if not source_image_path.exists():
                    console.print(f"⚠️  Image not found: {source_image_path}")
                    continue
                
                # Copy image to YOLOv8 images directory
                target_image_path = yolo_images_dir / image_filename
                shutil.copy2(source_image_path, target_image_path)
                
                # Create corresponding label file
                label_filename = Path(image_filename).stem + ".txt"
                label_path = yolo_labels_dir / label_filename
                
                # Convert annotations to YOLOv8 format
                yolo_annotations = []
                
                if image_id in image_annotations:
                    for ann in image_annotations[image_id]:
                        # Get bounding box in COCO format [x, y, width, height]
                        x, y, width, height = ann['bbox']
                        
                        # Convert to YOLOv8 format (normalized center_x, center_y, width, height)
                        center_x = (x + width / 2) / image_width
                        center_y = (y + height / 2) / image_height
                        norm_width = width / image_width
                        norm_height = height / image_height
                        
                        # Get class ID (map from COCO category ID to 0-based index)
                        coco_category_id = ann['category_id']
                        yolo_class_id = self.class_map[coco_category_id]
                        
                        # Create YOLOv8 annotation line
                        yolo_line = f"{yolo_class_id} {center_x:.6f} {center_y:.6f} {norm_width:.6f} {norm_height:.6f}"
                        yolo_annotations.append(yolo_line)
                
                # Write label file
                with open(label_path, 'w') as f:
                    f.write('\n'.join(yolo_annotations))
                
                processed_count += 1
            
            console.print(f"✅ Converted {processed_count} images for {split_name} split")
            return True
            
        except Exception as e:
            console.print(f"❌ Error converting {split_name} split: {e}")
            return False
    
    def create_yolo_dataset(self,
                          train_json: Path,
                          val_json: Path,
                          test_json: Path,
                          images_dir: Path,
                          output_dir: Path) -> bool:
        """Create complete YOLOv8 dataset from COCO splits.
        
        Args:
            train_json: Training COCO JSON
            val_json: Validation COCO JSON
            test_json: Test COCO JSON
            images_dir: Directory containing images
            output_dir: Output directory for YOLOv8 dataset
            
        Returns:
            True if successful, False otherwise
        """
        try:
            console.print("🚀 Creating YOLOv8 dataset from COCO splits...")
            
            # Convert each split
            splits = [
                (train_json, "train"),
                (val_json, "val"),
                (test_json, "test")
            ]
            
            for coco_json, split_name in splits:
                if not self.convert_coco_to_yolo(coco_json, images_dir, output_dir, split_name):
                    return False
            
            # Create class names file
            self._create_class_names_file(train_json, output_dir)
            
            console.print(f"✅ YOLOv8 dataset created successfully at: {output_dir}")
            return True
            
        except Exception as e:
            console.print(f"❌ Error creating YOLOv8 dataset: {e}")
            return False
    
    def _create_class_names_file(self, coco_json: Path, output_dir: Path):
        """Create class names file for YOLOv8."""
        try:
            with open(coco_json, 'r') as f:
                coco_data = json.load(f)
            
            # Sort categories by ID and create names list
            categories = sorted(coco_data['categories'], key=lambda x: x['id'])
            class_names = [cat['name'] for cat in categories]
            
            # Save class names
            class_names_path = output_dir / "class_names.txt"
            with open(class_names_path, 'w') as f:
                f.write('\n'.join(class_names))
            
            console.print(f"📝 Class names saved: {class_names_path}")
            console.print(f"   Total classes: {len(class_names)}")
            
        except Exception as e:
            console.print(f"⚠️  Warning: Could not create class names file: {e}")
    
    def create_yolo_config(self,
                         yolo_dataset_dir: Path,
                         output_path: Path) -> bool:
        """Create YOLOv8 data configuration file.
        
        Args:
            yolo_dataset_dir: Directory containing YOLOv8 dataset
            output_path: Path to save YAML config
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import yaml
            
            # Load class names
            class_names_file = yolo_dataset_dir / "class_names.txt"
            if class_names_file.exists():
                with open(class_names_file, 'r') as f:
                    class_names = [line.strip() for line in f.readlines()]
            else:
                console.print("⚠️  No class names file found, using default")
                class_names = [f"class_{i}" for i in range(80)]
            
            # Create YOLOv8 config
            config = {
                "path": str(yolo_dataset_dir.absolute()),
                "train": "images/train",
                "val": "images/val", 
                "test": "images/test",
                "nc": len(class_names),
                "names": {i: name for i, name in enumerate(class_names)}
            }
            
            # Save config
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            console.print(f"📋 YOLOv8 config saved: {output_path}")
            console.print(f"   Classes: {len(class_names)}")
            console.print(f"   Dataset path: {yolo_dataset_dir}")
            
            return True
            
        except Exception as e:
            console.print(f"❌ Error creating YOLOv8 config: {e}")
            return False


def convert_coco_to_yolo_format(train_json: Path,
                              val_json: Path,
                              test_json: Path,
                              images_dir: Path,
                              output_dir: Path,
                              config_output: Path) -> bool:
    """Convert COCO dataset to YOLOv8 format.
    
    Args:
        train_json: Training COCO JSON
        val_json: Validation COCO JSON
        test_json: Test COCO JSON
        images_dir: Directory containing images
        output_dir: Output directory for YOLOv8 dataset
        config_output: Path to save YOLOv8 config YAML
        
    Returns:
        True if successful, False otherwise
    """
    converter = COCOToYOLOConverter()
    
    # Create YOLOv8 dataset
    if not converter.create_yolo_dataset(
        train_json, val_json, test_json, images_dir, output_dir
    ):
        return False
    
    # Create YOLOv8 config
    if not converter.create_yolo_config(output_dir, config_output):
        return False
    
    return True 