#!/usr/bin/env python3
"""CGHD dataset setup script for CircuitCLI."""

import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from circuitcli.dataset.dvc_manager import DVCManager
from circuitcli.dataset.cghd_adapter import CGHDDatasetAdapter
from circuitcli.dataset.augmentation_loader import AugmentationLoader
from circuitcli.dataset.coco_validator import COCOValidator
from rich.console import Console

console = Console()


def main():
    """Run the CGHD dataset setup workflow."""
    console.print("🚀 CircuitCLI - CGHD Dataset Setup")
    console.print("=" * 50)
    
    # Check if CGHD dataset exists
    cghd_path = Path("data/cghd-zenodo-12")
    if not cghd_path.exists():
        console.print(f"❌ CGHD dataset not found at: {cghd_path}")
        console.print("Please ensure the CGHD dataset is properly downloaded and extracted.")
        return
    
    # Check for drafter directories
    drafter_dirs = list(cghd_path.glob("drafter_*"))
    if not drafter_dirs:
        console.print(f"❌ No drafter directories found in {cghd_path}")
        return
    
    console.print(f"✅ Found CGHD dataset with {len(drafter_dirs)} drafter directories")
    
    # Step 1: Initialize DVC (local only)
    console.print("\n📦 Step 1: Initializing DVC (local storage)...")
    try:
        dvc_manager = DVCManager()
        dvc_manager.initialize_dvc()
        console.print("✅ DVC initialized for local storage")
    except Exception as e:
        console.print(f"⚠️  DVC initialization warning: {e}")
    
    # Step 2: Process CGHD dataset
    console.print("\n🔄 Step 2: Processing CGHD dataset...")
    try:
        adapter = CGHDDatasetAdapter(cghd_path)
        
        if adapter.process_full_dataset():
            console.print("✅ CGHD dataset processing completed")
        else:
            console.print("❌ CGHD dataset processing failed")
            return
    except Exception as e:
        console.print(f"❌ Error processing CGHD dataset: {e}")
        return
    
    # Step 3: Validate processed datasets
    console.print("\n🔍 Step 3: Validating processed COCO datasets...")
    processed_splits = Path("data/processed/splits")
    processed_images = Path("data/processed/organized/images")
    
    validation_success = True
    for split in ["train", "val", "test"]:
        split_file = processed_splits / f"{split}.json"
        if split_file.exists():
            console.print(f"📋 Validating {split} split...")
            try:
                validator = COCOValidator(split_file, processed_images)
                if not validator.validate_all():
                    validation_success = False
            except Exception as e:
                console.print(f"❌ Error validating {split}: {e}")
                validation_success = False
        else:
            console.print(f"❌ Split file not found: {split_file}")
            validation_success = False
    
    if validation_success:
        console.print("✅ All dataset validations passed!")
    else:
        console.print("⚠️  Some validation issues found, but continuing...")
    
    # Step 4: Validate augmentation configuration
    console.print("\n🔍 Step 4: Validating augmentation configuration...")
    aug_config = Path("config/augmentations.yaml")
    if aug_config.exists():
        try:
            loader = AugmentationLoader(aug_config)
            if loader.validate_config():
                console.print("✅ Augmentation configuration validated")
            else:
                console.print("❌ Augmentation configuration validation failed")
        except Exception as e:
            console.print(f"❌ Error validating augmentation config: {e}")
    else:
        console.print("⚠️  Augmentation config not found, skipping validation")
    
    # Step 5: Add processed data to DVC tracking
    console.print("\n📦 Step 5: Adding processed data to DVC tracking...")
    try:
        processed_dir = Path("data/processed")
        if processed_dir.exists():
            dvc_manager.add_data_directory(processed_dir)
            console.print("✅ Processed data added to DVC tracking")
        else:
            console.print("⚠️  Processed data directory not found")
    except Exception as e:
        console.print(f"⚠️  DVC tracking warning: {e}")
    
    # Final summary
    console.print("\n🎉 CGHD Dataset Setup Complete!")
    console.print("=" * 50)
    
    # Check what was created
    processed_dir = Path("data/processed")
    if processed_dir.exists():
        splits_dir = processed_splits
        images_dir = processed_images
        
        console.print("📋 Summary of processed data:")
        
        # Count files
        if splits_dir.exists():
            train_file = splits_dir / "train.json"
            val_file = splits_dir / "val.json"  
            test_file = splits_dir / "test.json"
            
            console.print(f"   📄 Training split: {train_file} {'✅' if train_file.exists() else '❌'}")
            console.print(f"   📄 Validation split: {val_file} {'✅' if val_file.exists() else '❌'}")
            console.print(f"   📄 Test split: {test_file} {'✅' if test_file.exists() else '❌'}")
        
        if images_dir.exists():
            image_count = len(list(images_dir.glob("*.png"))) + len(list(images_dir.glob("*.jpg")))
            console.print(f"   🖼️  Total images: {image_count}")
        
        console.print(f"\n📁 All processed data in: {processed_dir}")
        
        # Show dataset info
        try:
            import json
            with open(processed_splits / "train.json", 'r') as f:
                train_data = json.load(f)
            
            console.print(f"📊 Dataset Statistics:")
            console.print(f"   - Categories: {len(train_data.get('categories', []))}")
            console.print(f"   - Training images: {len(train_data.get('images', []))}")
            console.print(f"   - Training annotations: {len(train_data.get('annotations', []))}")
            
        except Exception as e:
            console.print(f"⚠️  Could not load dataset statistics: {e}")
    
    console.print("\n💡 Next Steps:")
    console.print("   1. ✅ Dataset is ready for training!")
    console.print("   2. 🚀 Proceed to Phase 2: Detection & OCR Models")
    console.print("   3. 🔧 Use the following files for training:")
    console.print("      - Training: data/processed/splits/train.json")
    console.print("      - Validation: data/processed/splits/val.json")
    console.print("      - Test: data/processed/splits/test.json")
    console.print("      - Images: data/processed/organized/images/")
    
    console.print("\n🎯 Ready to train YOLOv8 models on your CGHD dataset!")


if __name__ == "__main__":
    main() 