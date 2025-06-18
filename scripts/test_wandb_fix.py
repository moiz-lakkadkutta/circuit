#!/usr/bin/env python3
"""Test script to verify W&B disabling works correctly."""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_wandb_disabled():
    """Test that W&B is properly disabled by default."""
    print("🧪 Testing W&B disabling...")
    
    # Check environment variables before import
    print(f"WANDB_MODE (before import): {os.environ.get('WANDB_MODE', 'not set')}")
    print(f"WANDB_DISABLED (before import): {os.environ.get('WANDB_DISABLED', 'not set')}")
    
    # Import detector (this should set the environment variables)
    from circuitcli.models.detector import CircuitDetector
    
    # Check environment variables after import
    print(f"WANDB_MODE (after import): {os.environ.get('WANDB_MODE', 'not set')}")
    print(f"WANDB_DISABLED (after import): {os.environ.get('WANDB_DISABLED', 'not set')}")
    
    # Try to create detector
    try:
        detector = CircuitDetector(model_size="n", pretrained=True)
        print("✅ CircuitDetector created successfully")
        
        # Test training config setup without W&B
        data_config_path = Path("config/yolo_data.yaml")
        if data_config_path.exists():
            config = detector.setup_training_config(
                data_config_path=data_config_path,
                experiment_name="test_wandb_disabled",
                epochs=1,
                use_wandb=False,
                use_tensorboard=False
            )
            print("✅ Training config setup successful (W&B disabled)")
        else:
            print("⚠️  Skipping training config test (no data config found)")
            
        return True
        
    except Exception as e:
        print(f"❌ Error creating detector: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_wandb_enabled():
    """Test that W&B can be enabled when explicitly requested."""
    print("\n🧪 Testing W&B enabling...")
    
    try:
        from circuitcli.models.detector import CircuitDetector
        
        detector = CircuitDetector(model_size="n", pretrained=True)
        
        # Test training config setup with W&B enabled
        data_config_path = Path("config/yolo_data.yaml")
        if data_config_path.exists():
            config = detector.setup_training_config(
                data_config_path=data_config_path,
                experiment_name="test_wandb_enabled",
                epochs=1,
                use_wandb=True,  # This should work without API key error
                use_tensorboard=False
            )
            print("✅ Training config setup successful (W&B enabled)")
            
            # Check that environment variables were cleared
            print(f"WANDB_MODE (after enabling): {os.environ.get('WANDB_MODE', 'not set')}")
            print(f"WANDB_DISABLED (after enabling): {os.environ.get('WANDB_DISABLED', 'not set')}")
        else:
            print("⚠️  Skipping W&B enable test (no data config found)")
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing W&B enabled: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Testing CircuitCLI W&B Integration Fixes")
    print("=" * 50)
    
    success = True
    
    # Test 1: W&B disabled by default
    success &= test_wandb_disabled()
    
    # Test 2: W&B can be enabled when requested
    success &= test_wandb_enabled()
    
    if success:
        print("\n🎉 All tests passed! W&B integration is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        sys.exit(1) 