#!/usr/bin/env python3
"""Test script for Phase 2 implementation validation."""

import sys
import json
from pathlib import Path
import torch
from PIL import Image
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from circuitcli.models.detector import CircuitDetector
from circuitcli.models.orientation_classifier import OrientationClassifier
from circuitcli.models.ocr_engine import CircuitOCR
from circuitcli.models.model_export import ModelExporter
from rich.console import Console

console = Console()


def test_detector_initialization():
    """Test YOLOv8 detector initialization."""
    console.print("🤖 Testing CircuitDetector initialization...")
    
    try:
        detector = CircuitDetector(model_size="n", pretrained=True)
        console.print("✅ CircuitDetector initialized successfully")
        
        # Test data config creation
        dummy_config = Path("test_yolo_config.yaml")
        dummy_train = Path("dummy_train.json")
        dummy_val = Path("dummy_val.json") 
        dummy_test = Path("dummy_test.json")
        dummy_images = Path("dummy_images")
        
        # Create minimal dummy files for testing
        dummy_coco = {
            "images": [{"id": 1, "file_name": "test.jpg", "width": 640, "height": 640}],
            "annotations": [{"id": 1, "image_id": 1, "category_id": 1, "bbox": [10, 10, 50, 50], "area": 2500}],
            "categories": [{"id": 1, "name": "resistor"}]
        }
        
        for json_file in [dummy_train, dummy_val, dummy_test]:
            with open(json_file, 'w') as f:
                json.dump(dummy_coco, f)
        
        dummy_images.mkdir(exist_ok=True)
        
        success = detector.create_data_config(
            dummy_train, dummy_val, dummy_test, dummy_images, dummy_config
        )
        
        if success:
            console.print("✅ Data config creation successful")
        
        # Cleanup
        for file in [dummy_config, dummy_train, dummy_val, dummy_test]:
            if file.exists():
                file.unlink()
        if dummy_images.exists():
            dummy_images.rmdir()
        
        return True
        
    except Exception as e:
        console.print(f"❌ CircuitDetector test failed: {e}")
        return False


def test_orientation_classifier():
    """Test orientation classifier initialization."""
    console.print("🧭 Testing OrientationClassifier...")
    
    try:
        classifier = OrientationClassifier(num_classes=4)
        console.print("✅ OrientationClassifier initialized successfully")
        
        # Test prediction with dummy image
        dummy_image = Image.new('RGB', (224, 224), color='white')
        predicted_class, confidence, orientation_label = classifier.predict(dummy_image)
        
        console.print(f"✅ Dummy prediction: {orientation_label} (confidence: {confidence:.2f})")
        
        return True
        
    except Exception as e:
        console.print(f"❌ OrientationClassifier test failed: {e}")
        return False


def test_ocr_engine():
    """Test OCR engine initialization."""
    console.print("🔤 Testing CircuitOCR...")
    
    try:
        # Try to initialize OCR (might fail if EasyOCR models not downloaded)
        ocr = CircuitOCR(languages=['en'], gpu=False)
        console.print("✅ CircuitOCR initialized successfully")
        
        # Test with dummy image
        dummy_image = np.ones((100, 200, 3), dtype=np.uint8) * 255
        
        # Test text extraction (might be empty with dummy image)
        text_detections = ocr.extract_text(dummy_image, preprocess=False, confidence_threshold=0.1)
        console.print(f"✅ OCR extraction completed (found {len(text_detections)} text regions)")
        
        return True
        
    except Exception as e:
        console.print(f"❌ CircuitOCR test failed: {e}")
        console.print("   Note: This might fail if EasyOCR models are not downloaded")
        return False


def test_model_export():
    """Test model export utilities."""
    console.print("📦 Testing ModelExporter...")
    
    try:
        exporter = ModelExporter()
        console.print("✅ ModelExporter initialized successfully")
        
        # Test ONNX verification with a simple model
        import torch.nn as nn
        
        class SimpleModel(nn.Module):
            def __init__(self):
                super().__init__()
                self.linear = nn.Linear(10, 1)
            
            def forward(self, x):
                return self.linear(x)
        
        # Create and export simple model
        model = SimpleModel()
        dummy_input = torch.randn(1, 10)
        
        test_onnx_path = Path("test_model.onnx")
        
        # Export to ONNX
        torch.onnx.export(
            model, dummy_input, str(test_onnx_path),
            input_names=['input'], output_names=['output']
        )
        
        # Verify ONNX
        success = exporter.verify_onnx_model(test_onnx_path, (10,))
        
        if success:
            console.print("✅ ONNX export and verification successful")
        
        # Cleanup
        if test_onnx_path.exists():
            test_onnx_path.unlink()
        
        return success
        
    except Exception as e:
        console.print(f"❌ ModelExporter test failed: {e}")
        return False


def test_dataset_availability():
    """Test if processed dataset is available."""
    console.print("📁 Testing dataset availability...")
    
    data_dir = Path("data/processed")
    splits_dir = data_dir / "splits"
    images_dir = data_dir / "organized" / "images"
    
    checks = [
        ("Data directory", data_dir.exists()),
        ("Splits directory", splits_dir.exists()),
        ("Images directory", images_dir.exists()),
        ("Train split", (splits_dir / "train.json").exists()),
        ("Val split", (splits_dir / "val.json").exists()),
        ("Test split", (splits_dir / "test.json").exists()),
    ]
    
    all_passed = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        console.print(f"   {status} {check_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        # Check dataset statistics
        try:
            with open(splits_dir / "train.json", 'r') as f:
                train_data = json.load(f)
            
            console.print(f"📊 Dataset Statistics:")
            console.print(f"   Training images: {len(train_data.get('images', []))}")
            console.print(f"   Training annotations: {len(train_data.get('annotations', []))}")
            console.print(f"   Categories: {len(train_data.get('categories', []))}")
            
        except Exception as e:
            console.print(f"⚠️  Could not load dataset statistics: {e}")
    
    return all_passed


def test_quick_training():
    """Test a quick training run with minimal epochs."""
    console.print("🏋️  Testing quick training run...")
    
    try:
        if not test_dataset_availability():
            console.print("❌ Skipping training test - dataset not available")
            return False
        
        # Initialize detector
        detector = CircuitDetector(model_size="n", pretrained=True)
        
        # Setup minimal training config
        data_config_path = Path("config/test_yolo_data.yaml")
        data_dir = Path("data/processed")
        splits_dir = data_dir / "splits" 
        images_dir = data_dir / "organized" / "images"
        
        # Create data config
        train_json = splits_dir / "train.json"
        val_json = splits_dir / "val.json"
        test_json = splits_dir / "test.json"
        
        detector.create_data_config(train_json, val_json, test_json, 
                                  images_dir, data_config_path)
        
        # Setup training with minimal parameters
        training_config = detector.setup_training_config(
            data_config_path=data_config_path,
            experiment_name="test_training",
            epochs=1,  # Just 1 epoch for testing
            batch_size=2,  # Small batch size
            img_size=320,  # Smaller image size
            learning_rate=0.01,
            patience=1,
            use_wandb=False,  # No W&B for testing
            use_tensorboard=False  # No TensorBoard for testing
        )
        
        console.print("✅ Training setup successful")
        console.print("   Note: This validates the training pipeline without full training")
        
        # Cleanup
        if data_config_path.exists():
            data_config_path.unlink()
        
        return True
        
    except Exception as e:
        console.print(f"❌ Quick training test failed: {e}")
        return False


def run_all_tests():
    """Run all Phase 2 implementation tests."""
    console.print("🚀 CircuitCLI Phase 2 Implementation Tests")
    console.print("=" * 60)
    
    tests = [
        ("Detector Initialization", test_detector_initialization),
        ("Orientation Classifier", test_orientation_classifier),
        ("OCR Engine", test_ocr_engine),
        ("Model Export", test_model_export),
        ("Dataset Availability", test_dataset_availability),
        ("Quick Training Setup", test_quick_training),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        console.print(f"\n📋 Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            console.print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    console.print("\n📊 Test Results Summary:")
    console.print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        console.print(f"   {status} {test_name}")
        if result:
            passed += 1
    
    console.print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        console.print("\n🎉 All tests passed! Phase 2 implementation is ready.")
        console.print("\n🚀 Next steps:")
        console.print("   1. Run: python scripts/train_detector.py --epochs 100 --use-wandb")
        console.print("   2. Monitor training progress in W&B dashboard")
        console.print("   3. Export best model to ONNX for deployment")
    else:
        console.print(f"\n⚠️  {len(results) - passed} tests failed. Please address issues before proceeding.")
    
    return passed == len(results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 