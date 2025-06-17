#!/usr/bin/env python3
"""
System setup script for CircuitCLI - handles different operating systems and environments.
This script prepares the system for training YOLOv8 models on electrical circuit datasets.
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
    from rich.table import Table
except ImportError:
    # Fallback if rich is not installed
    class Console:
        def print(self, *args, **kwargs):
            print(*args)
    
    console = Console()
else:
    console = Console()


class SystemSetup:
    """Handles system setup for CircuitCLI across different platforms."""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.python_version = sys.version_info
        self.is_conda = self._check_conda_env()
        self.has_gpu = self._check_gpu_availability()
        self.requirements = self._get_requirements()
        
    def _check_conda_env(self) -> bool:
        """Check if running in conda environment."""
        return 'CONDA_DEFAULT_ENV' in os.environ or 'conda' in sys.executable.lower()
    
    def _check_gpu_availability(self) -> Dict[str, bool]:
        """Check GPU availability for different frameworks."""
        gpu_info = {
            'cuda': False,
            'mps': False,  # Apple Silicon
            'cpu_only': True
        }
        
        try:
            import torch
            gpu_info['cuda'] = torch.cuda.is_available()
            gpu_info['mps'] = hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()
            gpu_info['cpu_only'] = not (gpu_info['cuda'] or gpu_info['mps'])
        except ImportError:
            pass
            
        return gpu_info
    
    def _get_requirements(self) -> Dict[str, List[str]]:
        """Get system-specific requirements."""
        base_requirements = [
            "torch>=2.1.0",
            "torchvision>=0.16.0",
            "ultralytics>=8.0.0",
            "opencv-python>=4.8.0",
            "pillow>=10.0.0",
            "numpy>=1.24.0",
            "pyyaml>=6.0",
            "tqdm>=4.65.0",
            "rich>=13.0.0",
            "wandb>=0.16.0",
            "tensorboardX>=2.6.0",
            "easyocr>=1.7.0",
            "onnx>=1.15.0",
            "onnxruntime>=1.16.0",
            "scikit-learn>=1.3.0",
            "matplotlib>=3.7.0",
            "seaborn>=0.12.0",
            "click>=8.1.0"
        ]
        
        # System-specific requirements
        system_requirements = {
            'linux': base_requirements + [
                "onnxruntime-gpu>=1.16.0" if self.has_gpu['cuda'] else "onnxruntime>=1.16.0"
            ],
            'darwin': base_requirements + [
                "onnxruntime>=1.16.0"  # MPS support varies
            ],
            'windows': base_requirements + [
                "onnxruntime-gpu>=1.16.0" if self.has_gpu['cuda'] else "onnxruntime>=1.16.0"
            ]
        }
        
        return system_requirements.get(self.system, base_requirements)
    
    def print_system_info(self):
        """Print comprehensive system information."""
        console.print("\n🔍 System Information", style="bold blue")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Component", style="cyan")
        table.add_column("Details", style="green")
        
        table.add_row("Operating System", f"{platform.system()} {platform.release()}")
        table.add_row("Architecture", platform.machine())
        table.add_row("Python Version", f"{self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}")
        table.add_row("Python Executable", sys.executable)
        table.add_row("Environment", "Conda" if self.is_conda else "Virtual Environment")
        table.add_row("CUDA Available", "✅ Yes" if self.has_gpu['cuda'] else "❌ No")
        table.add_row("MPS Available", "✅ Yes" if self.has_gpu['mps'] else "❌ No")
        table.add_row("Recommended Device", self._get_recommended_device())
        
        console.print(table)
    
    def _get_recommended_device(self) -> str:
        """Get recommended device for training."""
        if self.has_gpu['cuda']:
            return "cuda (NVIDIA GPU)"
        elif self.has_gpu['mps']:
            return "mps (Apple Silicon)"
        else:
            return "cpu (CPU only - slower training)"
    
    def install_dependencies(self, force_reinstall: bool = False):
        """Install system dependencies."""
        console.print("\n📦 Installing Dependencies", style="bold blue")
        
        # Check if requirements.txt exists
        req_file = Path("requirements.txt")
        if not req_file.exists():
            console.print("❌ requirements.txt not found. Creating it...")
            self._create_requirements_file()
        
        # Install command based on environment
        if self.is_conda:
            install_cmd = ["conda", "install", "--yes"]
            pip_cmd = ["conda", "run", "-n", os.environ.get('CONDA_DEFAULT_ENV', 'base'), "pip", "install"]
        else:
            install_cmd = [sys.executable, "-m", "pip", "install"]
            pip_cmd = install_cmd
        
        # Add force reinstall flag
        if force_reinstall:
            pip_cmd.extend(["--force-reinstall", "--no-cache-dir"])
        
        try:
            # Install from requirements.txt
            console.print("Installing packages from requirements.txt...")
            result = subprocess.run(
                pip_cmd + ["-r", "requirements.txt"],
                capture_output=True,
                text=True,
                check=True
            )
            console.print("✅ Dependencies installed successfully!")
            
        except subprocess.CalledProcessError as e:
            console.print(f"❌ Installation failed: {e}")
            console.print(f"Error output: {e.stderr}")
            return False
        
        return True
    
    def _create_requirements_file(self):
        """Create requirements.txt file."""
        req_content = "\n".join(self.requirements)
        with open("requirements.txt", "w") as f:
            f.write(req_content)
        console.print("✅ requirements.txt created")
    
    def verify_installation(self) -> bool:
        """Verify that all required packages are installed correctly."""
        console.print("\n🔍 Verifying Installation", style="bold blue")
        
        required_packages = [
            ("torch", "PyTorch"),
            ("torchvision", "TorchVision"),
            ("ultralytics", "YOLOv8"),
            ("cv2", "OpenCV"),
            ("PIL", "Pillow"),
            ("numpy", "NumPy"),
            ("yaml", "PyYAML"),
            ("wandb", "Weights & Biases"),
            ("tensorboardX", "TensorBoard"),
            ("easyocr", "EasyOCR"),
            ("onnx", "ONNX"),
            ("onnxruntime", "ONNX Runtime"),
            ("sklearn", "Scikit-learn"),
            ("matplotlib", "Matplotlib"),
            ("click", "Click")
        ]
        
        failed_imports = []
        
        for package, name in required_packages:
            try:
                __import__(package)
                console.print(f"✅ {name}")
            except ImportError:
                console.print(f"❌ {name}")
                failed_imports.append(name)
        
        if failed_imports:
            console.print(f"\n❌ Failed to import: {', '.join(failed_imports)}")
            return False
        
        # Test GPU availability
        try:
            import torch
            if torch.cuda.is_available():
                console.print(f"✅ CUDA GPU: {torch.cuda.get_device_name(0)}")
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                console.print("✅ Apple Silicon MPS")
            else:
                console.print("⚠️  CPU only (training will be slower)")
        except Exception as e:
            console.print(f"⚠️  GPU check failed: {e}")
        
        console.print("\n✅ Installation verification complete!")
        return True
    
    def setup_data_directories(self):
        """Setup required data directories."""
        console.print("\n📁 Setting up directories", style="bold blue")
        
        directories = [
            "data/processed",
            "data/processed/splits",
            "data/processed/organized/images",
            "data/processed/yolo_format",
            "models",
            "runs",
            "config",
            "logs"
        ]
        
        for dir_path in directories:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            console.print(f"✅ Created: {dir_path}")
    
    def create_training_scripts(self):
        """Create platform-specific training scripts."""
        console.print("\n📝 Creating training scripts", style="bold blue")
        
        # Bash script for Unix systems
        if self.system in ['linux', 'darwin']:
            bash_script = """#!/bin/bash
# CircuitCLI Training Script for Unix Systems

set -e  # Exit on error

echo "🚀 Starting CircuitCLI Training"
echo "================================"

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" && "$CONDA_DEFAULT_ENV" == "" ]]; then
    echo "⚠️  Warning: No virtual environment detected"
    echo "   Consider activating a virtual environment first"
fi

# Default parameters
EPOCHS=100
BATCH_SIZE=16
MODEL_SIZE="n"
EXPERIMENT_NAME="circuit_detection_$(date +%Y%m%d_%H%M%S)"
USE_WANDB=""
EXPORT_ONNX=""
DEVICE=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --epochs)
            EPOCHS="$2"
            shift 2
            ;;
        --batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --model-size)
            MODEL_SIZE="$2"
            shift 2
            ;;
        --experiment-name)
            EXPERIMENT_NAME="$2"
            shift 2
            ;;
        --use-wandb)
            USE_WANDB="--use-wandb"
            shift
            ;;
        --export-onnx)
            EXPORT_ONNX="--export-onnx"
            shift
            ;;
        --device)
            DEVICE="--device $2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --epochs N              Number of training epochs (default: 100)"
            echo "  --batch-size N          Batch size (default: 16)"
            echo "  --model-size SIZE       Model size: n,s,m,l,x (default: n)"
            echo "  --experiment-name NAME  Experiment name"
            echo "  --use-wandb            Enable Weights & Biases logging"
            echo "  --export-onnx          Export model to ONNX after training"
            echo "  --device DEVICE        Device: cpu, cuda, mps"
            echo "  --help                 Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "📊 Training Configuration:"
echo "   Epochs: $EPOCHS"
echo "   Batch Size: $BATCH_SIZE"
echo "   Model Size: YOLOv8$MODEL_SIZE"
echo "   Experiment: $EXPERIMENT_NAME"
echo "   W&B Logging: $([ -n "$USE_WANDB" ] && echo "Enabled" || echo "Disabled")"
echo "   ONNX Export: $([ -n "$EXPORT_ONNX" ] && echo "Enabled" || echo "Disabled")"
echo ""

# Run training
python scripts/train_detector.py \\
    --epochs $EPOCHS \\
    --batch-size $BATCH_SIZE \\
    --model-size $MODEL_SIZE \\
    --experiment-name $EXPERIMENT_NAME \\
    $USE_WANDB \\
    $EXPORT_ONNX \\
    $DEVICE

echo "✅ Training completed successfully!"
"""
            
            with open("train.sh", "w") as f:
                f.write(bash_script)
            
            # Make executable
            os.chmod("train.sh", 0o755)
            console.print("✅ Created: train.sh (Unix/Mac)")
        
        # Batch script for Windows
        if self.system == 'windows':
            batch_script = """@echo off
REM CircuitCLI Training Script for Windows

echo 🚀 Starting CircuitCLI Training
echo ================================

REM Default parameters
set EPOCHS=100
set BATCH_SIZE=16
set MODEL_SIZE=n
set EXPERIMENT_NAME=circuit_detection_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set USE_WANDB=
set EXPORT_ONNX=
set DEVICE=

REM Parse command line arguments (simplified)
:parse
if "%1"=="--epochs" (
    set EPOCHS=%2
    shift
    shift
    goto parse
)
if "%1"=="--batch-size" (
    set BATCH_SIZE=%2
    shift
    shift
    goto parse
)
if "%1"=="--model-size" (
    set MODEL_SIZE=%2
    shift
    shift
    goto parse
)
if "%1"=="--use-wandb" (
    set USE_WANDB=--use-wandb
    shift
    goto parse
)
if "%1"=="--export-onnx" (
    set EXPORT_ONNX=--export-onnx
    shift
    goto parse
)
if "%1"=="--help" (
    echo Usage: train.bat [OPTIONS]
    echo Options:
    echo   --epochs N              Number of training epochs (default: 100)
    echo   --batch-size N          Batch size (default: 16)
    echo   --model-size SIZE       Model size: n,s,m,l,x (default: n)
    echo   --use-wandb            Enable Weights ^& Biases logging
    echo   --export-onnx          Export model to ONNX after training
    echo   --help                 Show this help
    exit /b 0
)
if not "%1"=="" (
    shift
    goto parse
)

echo 📊 Training Configuration:
echo    Epochs: %EPOCHS%
echo    Batch Size: %BATCH_SIZE%
echo    Model Size: YOLOv8%MODEL_SIZE%
echo    Experiment: %EXPERIMENT_NAME%
echo.

REM Run training
python scripts/train_detector.py --epochs %EPOCHS% --batch-size %BATCH_SIZE% --model-size %MODEL_SIZE% --experiment-name %EXPERIMENT_NAME% %USE_WANDB% %EXPORT_ONNX% %DEVICE%

if %ERRORLEVEL% equ 0 (
    echo ✅ Training completed successfully!
) else (
    echo ❌ Training failed with error code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)
"""
            
            with open("train.bat", "w") as f:
                f.write(batch_script)
            console.print("✅ Created: train.bat (Windows)")
        
        # Python script (cross-platform)
        python_script = """#!/usr/bin/env python3
\"\"\"
Cross-platform training launcher for CircuitCLI.
This script provides a unified interface across different operating systems.
\"\"\"

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="CircuitCLI Training Launcher")
    parser.add_argument("--epochs", type=int, default=100, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Training batch size")
    parser.add_argument("--model-size", choices=["n", "s", "m", "l", "x"], default="n", help="YOLOv8 model size")
    parser.add_argument("--experiment-name", type=str, help="Experiment name")
    parser.add_argument("--use-wandb", action="store_true", help="Enable W&B logging")
    parser.add_argument("--export-onnx", action="store_true", help="Export to ONNX after training")
    parser.add_argument("--device", type=str, help="Training device (cpu, cuda, mps)")
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"), help="Data directory")
    
    args = parser.parse_args()
    
    # Generate experiment name if not provided
    if not args.experiment_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.experiment_name = f"circuit_detection_{timestamp}"
    
    # Build command
    cmd = [
        sys.executable, "scripts/train_detector.py",
        "--epochs", str(args.epochs),
        "--batch-size", str(args.batch_size),
        "--model-size", args.model_size,
        "--experiment-name", args.experiment_name,
        "--data-dir", str(args.data_dir)
    ]
    
    if args.use_wandb:
        cmd.append("--use-wandb")
    
    if args.export_onnx:
        cmd.append("--export-onnx")
    
    if args.device:
        cmd.extend(["--device", args.device])
    
    print("🚀 Starting CircuitCLI Training")
    print("=" * 50)
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # Run training
    try:
        result = subprocess.run(cmd, check=True)
        print("✅ Training completed successfully!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Training failed with exit code {e.returncode}")
        return e.returncode
    except KeyboardInterrupt:
        print("\\n⚠️  Training interrupted by user")
        return 1

if __name__ == "__main__":
    sys.exit(main())
"""
        
        with open("train.py", "w") as f:
            f.write(python_script)
        console.print("✅ Created: train.py (Cross-platform)")
    
    def create_deployment_guide(self):
        """Create comprehensive deployment documentation."""
        console.print("\n📖 Creating deployment guide", style="bold blue")
        
        guide_content = f"""# CircuitCLI Deployment Guide

## System Requirements

### Minimum Requirements
- **Python**: 3.9+ (3.10+ recommended)
- **RAM**: 8GB (16GB+ recommended for training)
- **Storage**: 10GB free space
- **OS**: Windows 10+, macOS 10.15+, Ubuntu 18.04+

### Recommended Requirements
- **GPU**: NVIDIA GPU with 6GB+ VRAM (RTX 3060 or better)
- **RAM**: 32GB for large datasets
- **Storage**: SSD with 50GB+ free space
- **CPU**: 8+ cores for faster data loading

## Quick Start

### 1. System Setup
```bash
# Clone/download the project
cd circuit2

# Run system setup
python scripts/setup_system.py

# Verify installation
python scripts/setup_system.py --verify-only
```

### 2. Data Preparation
Ensure your data is in the correct format:
```
data/processed/
├── splits/
│   ├── train.json
│   ├── val.json
│   └── test.json
└── organized/
    └── images/
        ├── image1.jpg
        ├── image2.jpg
        └── ...
```

### 3. Training

#### Option A: Using platform-specific scripts
```bash
# Unix/Mac
./train.sh --epochs 100 --use-wandb --export-onnx

# Windows
train.bat --epochs 100 --use-wandb --export-onnx
```

#### Option B: Using Python launcher
```bash
python train.py --epochs 100 --use-wandb --export-onnx
```

#### Option C: Direct Python execution
```bash
python scripts/train_detector.py --epochs 100 --use-wandb --export-onnx
```

## Platform-Specific Instructions

### Linux (Ubuntu/CentOS/RHEL)

#### Prerequisites
```bash
# Update system
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
# OR
sudo yum update -y  # CentOS/RHEL

# Install Python 3.9+
sudo apt install python3.9 python3.9-venv python3.9-dev  # Ubuntu
# OR
sudo yum install python39 python39-devel  # CentOS

# Install system dependencies
sudo apt install build-essential libgl1-mesa-glx libglib2.0-0  # Ubuntu
```

#### Setup
```bash
# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Run setup
python scripts/setup_system.py
```

#### GPU Support (NVIDIA)
```bash
# Install NVIDIA drivers and CUDA
# Follow: https://developer.nvidia.com/cuda-downloads

# Verify CUDA
nvidia-smi
nvcc --version
```

### macOS

#### Prerequisites
```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.10

# Install system dependencies
brew install libomp
```

#### Setup
```bash
# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Run setup
python scripts/setup_system.py
```

#### Apple Silicon (M1/M2/M3)
- MPS acceleration is automatically detected
- Some packages may need ARM64 versions
- Use `--device mps` for training

### Windows

#### Prerequisites
1. Install Python 3.9+ from [python.org](https://python.org)
2. Install Microsoft Visual C++ Build Tools
3. Install Git for Windows (optional)

#### Setup
```cmd
# Create virtual environment
python -m venv venv
venv\\Scripts\\activate

# Run setup
python scripts/setup_system.py
```

#### GPU Support (NVIDIA)
1. Install NVIDIA drivers
2. Install CUDA Toolkit from NVIDIA website
3. Verify installation: `nvidia-smi`

## Environment Variables

### Optional Configuration
```bash
# Weights & Biases API key
export WANDB_API_KEY="your_api_key_here"

# CUDA device selection
export CUDA_VISIBLE_DEVICES="0"

# Disable WANDB (if needed)
export WANDB_DISABLED=true
```

## Training Parameters

### Basic Parameters
- `--epochs`: Number of training epochs (default: 100)
- `--batch-size`: Training batch size (default: 16)
- `--model-size`: YOLOv8 model size (n/s/m/l/x, default: n)
- `--device`: Training device (cpu/cuda/mps, auto-detected)

### Advanced Parameters
- `--learning-rate`: Initial learning rate (default: 0.01)
- `--patience`: Early stopping patience (default: 50)
- `--img-size`: Input image size (default: 640)
- `--experiment-name`: Custom experiment name

### Logging Options
- `--use-wandb`: Enable Weights & Biases logging
- `--export-onnx`: Export model to ONNX format after training

## Hardware Recommendations

### GPU Training
| GPU | VRAM | Recommended Batch Size | Model Size |
|-----|------|----------------------|------------|
| RTX 3060 | 12GB | 8-16 | YOLOv8n/s |
| RTX 3070 | 8GB | 8-12 | YOLOv8n/s |
| RTX 3080 | 10GB | 16-24 | YOLOv8s/m |
| RTX 4090 | 24GB | 32-64 | YOLOv8m/l/x |
| A100 | 40GB | 64-128 | YOLOv8x |

### CPU Training
- Use smaller batch sizes (2-8)
- Expect 10-50x slower training
- Consider using YOLOv8n for faster training

## Troubleshooting

### Common Issues

#### 1. CUDA Out of Memory
```bash
# Reduce batch size
python train.py --batch-size 8

# Use smaller model
python train.py --model-size n
```

#### 2. Package Installation Errors
```bash
# Force reinstall
python scripts/setup_system.py --force-reinstall

# Manual installation
pip install --force-reinstall torch torchvision ultralytics
```

#### 3. Data Loading Errors
- Check data directory structure
- Verify image file formats (jpg, png, jpeg)
- Ensure COCO JSON files are valid

#### 4. Permission Errors (Linux/Mac)
```bash
# Make scripts executable
chmod +x train.sh
chmod +x scripts/*.py
```

### Performance Optimization

#### 1. Data Loading
```bash
# Use more workers (if you have enough CPU cores)
export YOLO_WORKERS=8
```

#### 2. Mixed Precision Training
- Automatically enabled for compatible GPUs
- Reduces memory usage and increases speed

#### 3. Model Optimization
- Start with YOLOv8n for prototyping
- Use YOLOv8s/m for production
- Only use YOLOv8l/x if you have sufficient resources

## Monitoring Training

### TensorBoard
```bash
# Start TensorBoard
tensorboard --logdir runs/

# Open http://localhost:6006
```

### Weights & Biases
1. Create account at [wandb.ai](https://wandb.ai)
2. Get API key from settings
3. Set environment variable: `export WANDB_API_KEY="your_key"`
4. Use `--use-wandb` flag when training

## Model Export and Deployment

### ONNX Export
```bash
# During training
python train.py --export-onnx

# After training
python scripts/export_model.py --checkpoint models/best.pt --format onnx
```

### Inference
```bash
# Run inference on new images
python scripts/predict.py --model models/best.onnx --source path/to/images/
```

## Support

### Getting Help
1. Check this deployment guide
2. Review error messages carefully
3. Check system requirements
4. Verify data format and structure
5. Try with smaller batch size or model

### System Information
```bash
# Get detailed system info
python scripts/setup_system.py --system-info
```

Current system detected: **{self.system.title()}**
Python version: **{self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}**
GPU support: **{self._get_recommended_device()}**
"""
        
        with open("DEPLOYMENT_GUIDE.md", "w") as f:
            f.write(guide_content)
        console.print("✅ Created: DEPLOYMENT_GUIDE.md")
    
    def run_full_setup(self, force_reinstall: bool = False):
        """Run complete system setup."""
        console.print(Panel.fit(
            "🚀 CircuitCLI System Setup\n"
            "Setting up your system for electrical circuit detection training",
            title="Welcome",
            border_style="blue"
        ))
        
        # Print system info
        self.print_system_info()
        
        # Setup directories
        self.setup_data_directories()
        
        # Install dependencies
        if not self.install_dependencies(force_reinstall):
            return False
        
        # Verify installation
        if not self.verify_installation():
            return False
        
        # Create training scripts
        self.create_training_scripts()
        
        # Create deployment guide
        self.create_deployment_guide()
        
        console.print(Panel.fit(
            "✅ Setup Complete!\n\n"
            f"🎯 Next steps:\n"
            f"1. Prepare your dataset in data/processed/\n"
            f"2. Run training: {'./train.sh' if self.system != 'windows' else 'train.bat'}\n"
            f"3. Monitor progress with TensorBoard or W&B\n\n"
            f"📖 See DEPLOYMENT_GUIDE.md for detailed instructions",
            title="Success",
            border_style="green"
        ))
        
        return True


def main():
    """Main setup function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CircuitCLI System Setup")
    parser.add_argument("--force-reinstall", action="store_true", 
                       help="Force reinstall all packages")
    parser.add_argument("--verify-only", action="store_true",
                       help="Only verify installation, don't install")
    parser.add_argument("--system-info", action="store_true",
                       help="Show system information only")
    
    args = parser.parse_args()
    
    setup = SystemSetup()
    
    if args.system_info:
        setup.print_system_info()
        return 0
    
    if args.verify_only:
        setup.print_system_info()
        success = setup.verify_installation()
        return 0 if success else 1
    
    # Run full setup
    success = setup.run_full_setup(args.force_reinstall)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 