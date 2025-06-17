"""CGHD (Circuit Graph Hand-Drawn) dataset adapter for CircuitCLI."""

import json
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import shutil
from rich.console import Console
from rich.progress import Progress

from .pascal_to_coco import PascalToCOCOConverter, create_train_val_test_splits
from .constants import DATASET_CONFIG

console = Console()


class CGHDDatasetAdapter:
    """Adapter to process the CGHD dataset for CircuitCLI pipeline."""
    
    def __init__(self, cghd_root: Path):
        """Initialize the CGHD adapter.
        
        Args:
            cghd_root: Root directory of the CGHD dataset.
        """
        self.cghd_root = Path(cghd_root)
        self.classes_map = self._load_cghd_classes()
        self.output_root = Path("data/processed")
        
    def _load_cghd_classes(self) -> Dict[str, int]:
        """Load CGHD class definitions."""
        classes_file = self.cghd_root / "classes.json"
        try:
            with open(classes_file, 'r') as f:
                classes = json.load(f)
            console.print(f"✅ Loaded {len(classes)} CGHD classes")
            return classes
        except Exception as e:
            console.print(f"❌ Error loading CGHD classes: {e}")
            raise
    
    def get_drafter_directories(self) -> List[Path]:
        """Get all drafter directories in the dataset."""
        drafter_dirs = []
        for item in self.cghd_root.iterdir():
            if item.is_dir() and item.name.startswith("drafter_"):
                drafter_dirs.append(item)
        
        drafter_dirs.sort(key=lambda x: int(x.name.split("_")[1]))
        console.print(f"📁 Found {len(drafter_dirs)} drafter directories")
        return drafter_dirs
    
    def organize_images_and_annotations(self, output_dir: Path) -> Tuple[Path, Path]:
        """Organize all images and annotations into unified directories.
        
        Args:
            output_dir: Output directory for organized data.
            
        Returns:
            Tuple of (images_dir, annotations_dir).
        """
        images_dir = output_dir / "images"
        annotations_dir = output_dir / "annotations"
        
        # Create output directories
        images_dir.mkdir(parents=True, exist_ok=True)
        annotations_dir.mkdir(parents=True, exist_ok=True)
        
        drafter_dirs = self.get_drafter_directories()
        
        total_images = 0
        total_annotations = 0
        
        with Progress(console=console) as progress:
            task = progress.add_task("Organizing CGHD dataset...", total=len(drafter_dirs))
            
            for drafter_dir in drafter_dirs:
                drafter_images = drafter_dir / "images"
                drafter_annotations = drafter_dir / "annotations"
                
                if drafter_images.exists() and drafter_annotations.exists():
                    # Copy images
                    for image_file in drafter_images.iterdir():
                        if image_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                            # Create unique filename with drafter prefix
                            new_name = f"{drafter_dir.name}_{image_file.name}"
                            dest_path = images_dir / new_name
                            
                            if not dest_path.exists():
                                shutil.copy2(image_file, dest_path)
                                total_images += 1
                    
                    # Copy annotations
                    for ann_file in drafter_annotations.iterdir():
                        if ann_file.suffix.lower() == '.xml':
                            # Create unique filename with drafter prefix
                            new_name = f"{drafter_dir.name}_{ann_file.name}"
                            dest_path = annotations_dir / new_name
                            
                            if not dest_path.exists():
                                shutil.copy2(ann_file, dest_path)
                                total_annotations += 1
                
                progress.advance(task)
        
        console.print(f"✅ Organized {total_images} images and {total_annotations} annotations")
        return images_dir, annotations_dir
    
    def create_class_mapping(self) -> Dict[str, int]:
        """Create mapping from CGHD classes to sequential IDs for COCO format."""
        # Filter out background class and create sequential mapping
        cghd_classes = {k: v for k, v in self.classes_map.items() if k != "__background__"}
        
        # Create sequential mapping starting from 1
        sequential_mapping = {}
        for idx, class_name in enumerate(sorted(cghd_classes.keys()), 1):
            sequential_mapping[class_name] = idx
        
        console.print(f"✅ Created sequential class mapping for {len(sequential_mapping)} classes")
        return sequential_mapping
    
    def update_xml_classes(self, annotations_dir: Path, class_mapping: Dict[str, int]) -> bool:
        """Update XML annotation files to use sequential class IDs.
        
        Args:
            annotations_dir: Directory containing XML annotation files.
            class_mapping: Mapping from class names to sequential IDs.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            import xml.etree.ElementTree as ET
            
            xml_files = list(annotations_dir.glob("*.xml"))
            updated_count = 0
            
            with Progress(console=console) as progress:
                task = progress.add_task("Updating XML class mappings...", total=len(xml_files))
                
                for xml_file in xml_files:
                    try:
                        tree = ET.parse(xml_file)
                        root = tree.getroot()
                        
                        modified = False
                        for obj in root.findall('object'):
                            name_elem = obj.find('name')
                            if name_elem is not None:
                                class_name = name_elem.text.strip()
                                if class_name in class_mapping:
                                    # Keep the original class name for COCO conversion
                                    modified = True
                                else:
                                    console.print(f"⚠️  Unknown class '{class_name}' in {xml_file.name}")
                        
                        if modified:
                            tree.write(xml_file, encoding='utf-8', xml_declaration=True)
                            updated_count += 1
                    
                    except Exception as e:
                        console.print(f"❌ Error processing {xml_file.name}: {e}")
                    
                    progress.advance(task)
            
            console.print(f"✅ Updated {updated_count} XML files")
            return True
            
        except Exception as e:
            console.print(f"❌ Error updating XML classes: {e}")
            return False
    
    def convert_to_coco(self, images_dir: Path, annotations_dir: Path, output_path: Path) -> bool:
        """Convert CGHD dataset to COCO format.
        
        Args:
            images_dir: Directory containing organized images.
            annotations_dir: Directory containing organized annotations.
            output_path: Output path for COCO JSON file.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Create custom converter that uses CGHD classes
            converter = CGHDToCOCOConverter(images_dir, annotations_dir, self.classes_map)
            return converter.convert_dataset(output_path)
            
        except Exception as e:
            console.print(f"❌ Error converting to COCO: {e}")
            return False
    
    def process_full_dataset(self, 
                           train_ratio: float = 0.7,
                           val_ratio: float = 0.2,
                           test_ratio: float = 0.1,
                           random_seed: int = 42) -> bool:
        """Process the complete CGHD dataset.
        
        Args:
            train_ratio: Ratio for training set.
            val_ratio: Ratio for validation set.
            test_ratio: Ratio for test set.
            random_seed: Random seed for reproducible splits.
            
        Returns:
            True if successful, False otherwise.
        """
        console.print("🚀 Starting CGHD dataset processing...")
        
        # Step 1: Organize images and annotations
        console.print("\n📁 Step 1: Organizing images and annotations...")
        organized_dir = self.output_root / "organized"
        images_dir, annotations_dir = self.organize_images_and_annotations(organized_dir)
        
        # Step 2: Convert to COCO format
        console.print("\n🔄 Step 2: Converting to COCO format...")
        coco_output = self.output_root / "annotations" / "dataset.json"
        coco_output.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.convert_to_coco(images_dir, annotations_dir, coco_output):
            return False
        
        # Step 3: Create train/val/test splits
        console.print("\n📊 Step 3: Creating dataset splits...")
        splits_dir = self.output_root / "splits"
        if not create_train_val_test_splits(
            coco_output, splits_dir, train_ratio, val_ratio, test_ratio, random_seed
        ):
            return False
        
        # Step 4: Generate dataset statistics
        console.print("\n📈 Step 4: Generating dataset statistics...")
        self._generate_statistics(coco_output)
        
        console.print("\n🎉 CGHD dataset processing completed successfully!")
        console.print(f"📁 Processed data available in: {self.output_root}")
        console.print("📄 Files created:")
        console.print(f"   - {coco_output}")
        console.print(f"   - {splits_dir}/train.json")
        console.print(f"   - {splits_dir}/val.json")
        console.print(f"   - {splits_dir}/test.json")
        
        return True
    
    def _generate_statistics(self, coco_json_path: Path):
        """Generate and display dataset statistics."""
        try:
            with open(coco_json_path, 'r') as f:
                coco_data = json.load(f)
            
            from rich.table import Table
            
            # Create statistics table
            stats_table = Table(title="CGHD Dataset Statistics")
            stats_table.add_column("Metric", style="cyan")
            stats_table.add_column("Value", style="magenta")
            
            stats_table.add_row("Total Images", str(len(coco_data["images"])))
            stats_table.add_row("Total Annotations", str(len(coco_data["annotations"])))
            stats_table.add_row("Total Categories", str(len(coco_data["categories"])))
            
            # Category distribution
            from collections import defaultdict
            category_counts = defaultdict(int)
            for annotation in coco_data["annotations"]:
                category_counts[annotation["category_id"]] += 1
            
            # Find most common categories
            category_lookup = {cat["id"]: cat["name"] for cat in coco_data["categories"]}
            sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
            
            if sorted_categories:
                most_common = category_lookup[sorted_categories[0][0]]
                stats_table.add_row("Most Common Class", f"{most_common} ({sorted_categories[0][1]})")
            
            console.print(stats_table)
            
        except Exception as e:
            console.print(f"⚠️  Could not generate statistics: {e}")


class CGHDToCOCOConverter(PascalToCOCOConverter):
    """Specialized COCO converter for CGHD dataset."""
    
    def __init__(self, images_dir: Path, annotations_dir: Path, cghd_classes: Dict[str, int]):
        """Initialize CGHD-specific converter."""
        super().__init__(images_dir, annotations_dir)
        self.cghd_classes = cghd_classes
        
        # Override category creation to use CGHD classes
        self.coco_data["categories"] = []
        self.category_map = self._create_cghd_category_map()
    
    def _create_cghd_category_map(self) -> Dict[str, int]:
        """Create COCO categories from CGHD classes."""
        category_map = {}
        
        # Filter out background and create categories
        for class_name, class_id in self.cghd_classes.items():
            if class_name != "__background__":
                category_info = {
                    "id": class_id,
                    "name": class_name,
                    "supercategory": "electrical_component"
                }
                self.coco_data["categories"].append(category_info)
                category_map[class_name] = class_id
        
        console.print(f"✅ Created {len(category_map)} CGHD categories for COCO")
        return category_map 