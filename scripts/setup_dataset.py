#!/usr/bin/env python3
"""Standalone dataset setup script for CircuitCLI."""

import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from circuitcli.dataset.dvc_manager import DVCManager
from circuitcli.dataset.pascal_to_coco import PascalToCOCOConverter, create_train_val_test_splits
from circuitcli.dataset.synthetic_generator import SyntheticSchematicGenerator
from circuitcli.dataset.augmentation_loader import AugmentationLoader
from circuitcli.dataset.coco_validator import COCOValidator
from rich.console import Console

console = Console()


def main():
    """Run the complete dataset setup workflow."""
    console.print("🚀 CircuitCLI Dataset Setup")
    console.print("=" * 50)
    
    # Create necessary directories
    directories = [
        "data/raw/images",
        "data/raw/annotations", 
        "data/annotations",
        "data/splits",
        "data/synthetic",
        "config"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        console.print(f"📁 Created directory: {dir_path}")
    
    # Check if raw data exists
    raw_images = Path("data/raw/images")
    raw_annotations = Path("data/raw/annotations")
    
    if not any(raw_images.iterdir()) or not any(raw_annotations.iterdir()):
        console.print("\n⚠️  No raw data found!")
        console.print("Please place your images and Pascal VOC XML files in:")
        console.print(f"   Images: {raw_images}")
        console.print(f"   Annotations: {raw_annotations}")
        console.print("\nYou can still proceed to test the other components.")
        console.print("Would you like to continue with synthetic data generation? [y/N]")
        
        response = input().lower().strip()
        if response != 'y':
            console.print("👋 Setup cancelled. Add your data and run again.")
            return
    
    # Step 1: Initialize DVC
    console.print("\n📦 Step 1: Initializing DVC...")
    try:
        dvc_manager = DVCManager()
        dvc_manager.initialize_dvc()
        console.print("✅ DVC initialized")
    except Exception as e:
        console.print(f"⚠️  DVC initialization warning: {e}")
    
    # Step 2: Convert Pascal VOC to COCO (if data exists)
    if raw_images.exists() and any(raw_images.iterdir()):
        console.print("\n🔄 Step 2: Converting Pascal VOC to COCO...")
        try:
            converter = PascalToCOCOConverter(raw_images, raw_annotations)
            coco_output = Path("data/annotations/dataset.json")
            
            if converter.convert_dataset(coco_output):
                console.print("✅ Pascal VOC to COCO conversion completed")
                
                # Step 3: Create splits
                console.print("\n📊 Step 3: Creating dataset splits...")
                splits_dir = Path("data/splits")
                if create_train_val_test_splits(coco_output, splits_dir):
                    console.print("✅ Dataset splits created")
                    
                    # Step 4: Validate COCO datasets
                    console.print("\n🔍 Step 4: Validating COCO datasets...")
                    for split in ["train", "val", "test"]:
                        split_file = splits_dir / f"{split}.json"
                        if split_file.exists():
                            console.print(f"Validating {split} split...")
                            validator = COCOValidator(split_file, raw_images)
                            validator.validate_all()
                else:
                    console.print("❌ Failed to create splits")
            else:
                console.print("❌ Pascal VOC conversion failed")
        except Exception as e:
            console.print(f"❌ Error in Pascal VOC conversion: {e}")
    
    # Step 5: Generate synthetic data
    console.print("\n🎨 Step 5: Generating synthetic schematic data...")
    try:
        synthetic_dir = Path("data/synthetic")
        generator = SyntheticSchematicGenerator(synthetic_dir)
        if generator.generate_dataset(20):  # Generate 20 samples for testing
            console.print("✅ Synthetic data generation completed")
        else:
            console.print("❌ Synthetic data generation failed")
    except Exception as e:
        console.print(f"❌ Error in synthetic generation: {e}")
    
    # Step 6: Validate augmentation config
    console.print("\n🔍 Step 6: Validating augmentation configuration...")
    try:
        aug_config = Path("config/augmentations.yaml")
        if aug_config.exists():
            loader = AugmentationLoader(aug_config)
            if loader.validate_config():
                console.print("✅ Augmentation configuration validated")
            else:
                console.print("❌ Augmentation configuration validation failed")
        else:
            console.print("⚠️  Augmentation config not found, skipping validation")
    except Exception as e:
        console.print(f"❌ Error validating augmentation config: {e}")
    
    # Step 7: Add to DVC tracking
    console.print("\n📦 Step 7: Adding data to DVC tracking...")
    try:
        data_dir = Path("data")
        if data_dir.exists():
            dvc_manager.add_data_directory(data_dir)
            console.print("✅ Data added to DVC tracking")
    except Exception as e:
        console.print(f"⚠️  DVC tracking warning: {e}")
    
    # Final summary
    console.print("\n🎉 Dataset Setup Complete!")
    console.print("=" * 50)
    console.print("📋 Summary of what was created:")
    console.print("   📁 Directory structure")
    console.print("   📄 COCO JSON files (if raw data provided)")
    console.print("   📊 Train/Val/Test splits")
    console.print("   🎨 Synthetic images")
    console.print("   🔧 DVC configuration")
    
    console.print("\n💡 Next Steps:")
    console.print("   1. Review generated files in data/ directory")
    console.print("   2. Add raw images and annotations if not done already")
    console.print("   3. Configure DVC remote storage:")
    console.print("      dvc remote add -d myremote s3://your-bucket/path")
    console.print("   4. Commit DVC files to Git")
    console.print("   5. Start model training!")
    
    console.print("\n🚀 Ready to begin Phase 2: Detection & OCR Models!")


if __name__ == "__main__":
    main() 