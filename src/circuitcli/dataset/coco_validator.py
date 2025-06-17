"""COCO dataset validation utilities."""

import json
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict
import numpy as np
from PIL import Image
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval

console = Console()


class COCOValidator:
    """Validate COCO dataset format and content."""
    
    def __init__(self, coco_json_path: Path, images_dir: Optional[Path] = None):
        """Initialize the validator.
        
        Args:
            coco_json_path: Path to the COCO JSON file.
            images_dir: Optional path to images directory for file validation.
        """
        self.coco_json_path = Path(coco_json_path)
        self.images_dir = Path(images_dir) if images_dir else None
        self.coco_data = None
        self.coco_api = None
        
    def load_coco_data(self) -> bool:
        """Load COCO data from JSON file.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            with open(self.coco_json_path, 'r') as f:
                self.coco_data = json.load(f)
            
            # Initialize COCO API
            self.coco_api = COCO(str(self.coco_json_path))
            
            console.print(f"✅ Loaded COCO data from {self.coco_json_path}")
            return True
            
        except Exception as e:
            console.print(f"❌ Error loading COCO data: {e}")
            return False
    
    def validate_structure(self) -> bool:
        """Validate COCO JSON structure.
        
        Returns:
            True if structure is valid, False otherwise.
        """
        if self.coco_data is None:
            console.print("❌ COCO data not loaded")
            return False
        
        required_keys = ["info", "licenses", "categories", "images", "annotations"]
        missing_keys = [key for key in required_keys if key not in self.coco_data]
        
        if missing_keys:
            console.print(f"❌ Missing required keys: {missing_keys}")
            return False
        
        # Validate info section
        info_required = ["description", "version", "year", "contributor", "date_created"]
        info_missing = [key for key in info_required if key not in self.coco_data["info"]]
        
        if info_missing:
            console.print(f"⚠️  Missing info fields: {info_missing}")
        
        # Validate categories
        if not self.coco_data["categories"]:
            console.print("❌ No categories defined")
            return False
        
        for category in self.coco_data["categories"]:
            if not all(key in category for key in ["id", "name"]):
                console.print("❌ Invalid category structure")
                return False
        
        # Validate images
        if not self.coco_data["images"]:
            console.print("❌ No images defined")
            return False
        
        for image in self.coco_data["images"]:
            if not all(key in image for key in ["id", "width", "height", "file_name"]):
                console.print("❌ Invalid image structure")
                return False
        
        # Validate annotations
        for annotation in self.coco_data["annotations"]:
            required_ann_keys = ["id", "image_id", "category_id", "bbox", "area"]
            if not all(key in annotation for key in required_ann_keys):
                console.print("❌ Invalid annotation structure")
                return False
        
        console.print("✅ COCO structure validation passed")
        return True
    
    def validate_consistency(self) -> bool:
        """Validate data consistency (IDs, references, etc.).
        
        Returns:
            True if consistent, False otherwise.
        """
        if self.coco_data is None:
            return False
        
        # Check for unique IDs
        image_ids = [img["id"] for img in self.coco_data["images"]]
        if len(image_ids) != len(set(image_ids)):
            console.print("❌ Duplicate image IDs found")
            return False
        
        annotation_ids = [ann["id"] for ann in self.coco_data["annotations"]]
        if len(annotation_ids) != len(set(annotation_ids)):
            console.print("❌ Duplicate annotation IDs found")
            return False
        
        category_ids = [cat["id"] for cat in self.coco_data["categories"]]
        if len(category_ids) != len(set(category_ids)):
            console.print("❌ Duplicate category IDs found")
            return False
        
        # Check reference consistency
        valid_image_ids = set(image_ids)
        valid_category_ids = set(category_ids)
        
        invalid_refs = []
        for annotation in self.coco_data["annotations"]:
            if annotation["image_id"] not in valid_image_ids:
                invalid_refs.append(f"Annotation {annotation['id']} references invalid image ID")
            if annotation["category_id"] not in valid_category_ids:
                invalid_refs.append(f"Annotation {annotation['id']} references invalid category ID")
        
        if invalid_refs:
            console.print("❌ Reference consistency errors:")
            for error in invalid_refs[:5]:  # Show first 5 errors
                console.print(f"   {error}")
            if len(invalid_refs) > 5:
                console.print(f"   ... and {len(invalid_refs) - 5} more")
            return False
        
        console.print("✅ Data consistency validation passed")
        return True
    
    def validate_bounding_boxes(self) -> bool:
        """Validate bounding box coordinates and areas.
        
        Returns:
            True if valid, False otherwise.
        """
        if self.coco_data is None:
            return False
        
        # Create image lookup
        image_lookup = {img["id"]: img for img in self.coco_data["images"]}
        
        invalid_bboxes = []
        for annotation in self.coco_data["annotations"]:
            bbox = annotation["bbox"]
            image_id = annotation["image_id"]
            
            if image_id not in image_lookup:
                continue
            
            image_info = image_lookup[image_id]
            img_width, img_height = image_info["width"], image_info["height"]
            
            x, y, w, h = bbox
            
            # Check if bbox is within image bounds
            if x < 0 or y < 0 or x + w > img_width or y + h > img_height:
                invalid_bboxes.append(f"Annotation {annotation['id']}: bbox out of bounds")
            
            # Check if bbox has positive area
            if w <= 0 or h <= 0:
                invalid_bboxes.append(f"Annotation {annotation['id']}: invalid bbox dimensions")
            
            # Check if computed area matches annotation area
            computed_area = w * h
            if abs(computed_area - annotation["area"]) > 1:  # Allow small floating point errors
                invalid_bboxes.append(f"Annotation {annotation['id']}: area mismatch")
        
        if invalid_bboxes:
            console.print("❌ Bounding box validation errors:")
            for error in invalid_bboxes[:5]:
                console.print(f"   {error}")
            if len(invalid_bboxes) > 5:
                console.print(f"   ... and {len(invalid_bboxes) - 5} more")
            return False
        
        console.print("✅ Bounding box validation passed")
        return True
    
    def validate_image_files(self) -> bool:
        """Validate that image files exist and match metadata.
        
        Returns:
            True if all files are valid, False otherwise.
        """
        if self.images_dir is None:
            console.print("⚠️  No images directory provided, skipping file validation")
            return True
        
        if self.coco_data is None:
            return False
        
        missing_files = []
        dimension_mismatches = []
        
        with Progress(console=console) as progress:
            task = progress.add_task("Validating image files...", total=len(self.coco_data["images"]))
            
            for image_info in self.coco_data["images"]:
                image_path = self.images_dir / image_info["file_name"]
                
                # Check if file exists
                if not image_path.exists():
                    missing_files.append(image_info["file_name"])
                else:
                    # Check dimensions
                    try:
                        with Image.open(image_path) as img:
                            actual_width, actual_height = img.size
                            if (actual_width != image_info["width"] or 
                                actual_height != image_info["height"]):
                                dimension_mismatches.append(
                                    f"{image_info['file_name']}: "
                                    f"expected {image_info['width']}x{image_info['height']}, "
                                    f"got {actual_width}x{actual_height}"
                                )
                    except Exception as e:
                        missing_files.append(f"{image_info['file_name']} (corrupt: {e})")
                
                progress.advance(task)
        
        has_errors = False
        
        if missing_files:
            console.print("❌ Missing or corrupt image files:")
            for file in missing_files[:5]:
                console.print(f"   {file}")
            if len(missing_files) > 5:
                console.print(f"   ... and {len(missing_files) - 5} more")
            has_errors = True
        
        if dimension_mismatches:
            console.print("❌ Image dimension mismatches:")
            for mismatch in dimension_mismatches[:5]:
                console.print(f"   {mismatch}")
            if len(dimension_mismatches) > 5:
                console.print(f"   ... and {len(dimension_mismatches) - 5} more")
            has_errors = True
        
        if not has_errors:
            console.print("✅ Image file validation passed")
        
        return not has_errors
    
    def generate_statistics(self) -> Dict[str, Any]:
        """Generate dataset statistics.
        
        Returns:
            Dictionary with dataset statistics.
        """
        if self.coco_data is None:
            return {}
        
        stats = {
            "total_images": len(self.coco_data["images"]),
            "total_annotations": len(self.coco_data["annotations"]),
            "total_categories": len(self.coco_data["categories"]),
        }
        
        # Category distribution
        category_counts = defaultdict(int)
        for annotation in self.coco_data["annotations"]:
            category_counts[annotation["category_id"]] += 1
        
        # Create category name lookup
        category_lookup = {cat["id"]: cat["name"] for cat in self.coco_data["categories"]}
        
        stats["category_distribution"] = {
            category_lookup[cat_id]: count 
            for cat_id, count in category_counts.items()
        }
        
        # Image size distribution
        widths = [img["width"] for img in self.coco_data["images"]]
        heights = [img["height"] for img in self.coco_data["images"]]
        
        stats["image_dimensions"] = {
            "width_range": [min(widths), max(widths)],
            "height_range": [min(heights), max(heights)],
            "avg_width": np.mean(widths),
            "avg_height": np.mean(heights),
        }
        
        # Annotation statistics
        areas = [ann["area"] for ann in self.coco_data["annotations"]]
        if areas:
            stats["annotation_areas"] = {
                "min_area": min(areas),
                "max_area": max(areas),
                "avg_area": np.mean(areas),
                "median_area": np.median(areas),
            }
        
        # Annotations per image
        annotations_per_image = defaultdict(int)
        for annotation in self.coco_data["annotations"]:
            annotations_per_image[annotation["image_id"]] += 1
        
        ann_counts = list(annotations_per_image.values())
        if ann_counts:
            stats["annotations_per_image"] = {
                "min": min(ann_counts),
                "max": max(ann_counts),
                "avg": np.mean(ann_counts),
                "median": np.median(ann_counts),
            }
        
        return stats
    
    def print_statistics(self):
        """Print dataset statistics in a formatted table."""
        stats = self.generate_statistics()
        
        if not stats:
            console.print("❌ No statistics available")
            return
        
        # General statistics table
        general_table = Table(title="Dataset Overview")
        general_table.add_column("Metric", style="cyan")
        general_table.add_column("Value", style="magenta")
        
        general_table.add_row("Total Images", str(stats["total_images"]))
        general_table.add_row("Total Annotations", str(stats["total_annotations"]))
        general_table.add_row("Total Categories", str(stats["total_categories"]))
        
        if "annotations_per_image" in stats:
            api = stats["annotations_per_image"]
            general_table.add_row("Avg Annotations/Image", f"{api['avg']:.2f}")
        
        console.print(general_table)
        
        # Category distribution table
        if "category_distribution" in stats:
            cat_table = Table(title="Category Distribution")
            cat_table.add_column("Category", style="cyan")
            cat_table.add_column("Count", style="magenta")
            cat_table.add_column("Percentage", style="green")
            
            total_annotations = stats["total_annotations"]
            for category, count in sorted(stats["category_distribution"].items(), 
                                        key=lambda x: x[1], reverse=True):
                percentage = (count / total_annotations) * 100
                cat_table.add_row(category, str(count), f"{percentage:.1f}%")
            
            console.print(cat_table)
    
    def validate_all(self) -> bool:
        """Run all validation checks.
        
        Returns:
            True if all validations pass, False otherwise.
        """
        console.print("🔍 Starting COCO dataset validation...")
        
        if not self.load_coco_data():
            return False
        
        validations = [
            ("Structure", self.validate_structure),
            ("Consistency", self.validate_consistency),
            ("Bounding Boxes", self.validate_bounding_boxes),
            ("Image Files", self.validate_image_files),
        ]
        
        all_passed = True
        for name, validator in validations:
            console.print(f"\n📋 Validating {name}...")
            if not validator():
                all_passed = False
        
        if all_passed:
            console.print("\n🎉 All validations passed!")
            self.print_statistics()
        else:
            console.print("\n❌ Some validations failed")
        
        return all_passed 