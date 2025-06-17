#!/usr/bin/env python3
"""Installation script for CircuitCLI Phase 2 dependencies."""

import subprocess
import sys
import platform
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Command: {command}")
        print(f"   Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major != 3 or version.minor < 9:
        print(f"❌ Python 3.9+ required, found {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def detect_gpu():
    """Detect if CUDA GPU is available."""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            print(f"🚀 CUDA GPU detected: {gpu_name}")
            return True
    except ImportError:
        pass
    
    print("💻 No CUDA GPU detected, will use CPU versions")
    return False

def install_dependencies():
    """Install all dependencies from requirements.txt."""
    print("📦 Installing CircuitCLI Phase 2 Dependencies")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Check if requirements.txt exists
    req_file = Path("requirements.txt")
    if not req_file.exists():
        print(f"❌ requirements.txt not found in {Path.cwd()}")
        print("   Please run this script from the project root directory")
        return False
    
    # Upgrade pip first
    if not run_command(f"{sys.executable} -m pip install --upgrade pip", "Upgrading pip"):
        return False
    
    # Install basic dependencies
    if not run_command(f"{sys.executable} -m pip install -r requirements.txt", "Installing dependencies from requirements.txt"):
        return False
    
    # Check if we should install CUDA versions
    has_gpu = detect_gpu()
    
    if has_gpu:
        print("\n🚀 Installing CUDA-optimized PyTorch...")
        cuda_command = f"{sys.executable} -m pip install torch==2.1.2+cu118 torchvision==0.16.2+cu118 --extra-index-url https://download.pytorch.org/whl/cu118"
        run_command(cuda_command, "Installing CUDA PyTorch")
    
    print("\n🎉 Installation completed!")
    return True

def verify_installation():
    """Verify that key packages are installed correctly."""
    print("\n🔍 Verifying installation...")
    
    critical_packages = [
        "torch",
        "torchvision", 
        "ultralytics",
        "opencv-python",
        "wandb",
        "tensorboardX",
        "easyocr",
        "onnx",
        "onnxruntime",
    ]
    
    failed_packages = []
    
    for package in critical_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package}")
            failed_packages.append(package)
    
    if failed_packages:
        print(f"\n⚠️  Failed to import: {', '.join(failed_packages)}")
        print("   Try installing them manually:")
        for pkg in failed_packages:
            print(f"   pip install {pkg}")
        return False
    
    print("\n✅ All critical packages verified successfully!")
    return True

def setup_wandb():
    """Setup Weights & Biases (optional)."""
    print("\n🌐 Setting up Weights & Biases (optional)...")
    print("   Visit https://wandb.ai/settings to get your API key")
    
    try:
        import wandb
        if run_command("wandb --version", "Checking W&B installation"):
            print("   Run 'wandb login' to authenticate (optional)")
        return True
    except ImportError:
        print("   ❌ W&B not available")
        return False

def main():
    """Main installation process."""
    print("🚀 CircuitCLI Phase 2 Dependency Installer")
    print("=" * 50)
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version}")
    print(f"Working directory: {Path.cwd()}")
    
    success = True
    
    # Install dependencies
    success = install_dependencies() and success
    
    # Verify installation
    success = verify_installation() and success
    
    # Setup W&B (optional)
    setup_wandb()
    
    if success:
        print("\n🎉 Setup completed successfully!")
        print("\n🚀 Next steps:")
        print("   1. Test installation: python scripts/test_phase2_implementation.py")
        print("   2. Start training: python scripts/train_detector.py --epochs 100")
        print("   3. Optional: Run 'wandb login' for experiment tracking")
        return 0
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 