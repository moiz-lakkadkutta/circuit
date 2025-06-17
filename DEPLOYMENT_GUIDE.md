# CircuitCLI Deployment Guide

## Quick Start for Different Systems

### 🐧 Linux (Ubuntu/CentOS/RHEL)

```bash
# 1. System setup
sudo apt update && sudo apt upgrade -y
sudo apt install python3.9 python3.9-venv python3.9-dev build-essential

# 2. Project setup
cd circuit2
python3.9 -m venv venv
source venv/bin/activate

# 3. Install dependencies
python scripts/setup_system.py

# 4. Start training
./train.sh --epochs 100 --use-wandb --export-onnx
```

### 🍎 macOS (Intel & Apple Silicon)

```bash
# 1. Install Homebrew (if needed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install Python
brew install python@3.10

# 3. Project setup
cd circuit2
python3.10 -m venv venv
source venv/bin/activate

# 4. Install dependencies
python scripts/setup_system.py

# 5. Start training (Apple Silicon will use MPS automatically)
./train.sh --epochs 100 --use-wandb --export-onnx
```

### 🪟 Windows

```cmd
REM 1. Download Python 3.9+ from python.org and install
REM 2. Open Command Prompt or PowerShell

REM 3. Project setup
cd circuit2
python -m venv venv
venv\Scripts\activate

REM 4. Install dependencies
python scripts/setup_system.py

REM 5. Start training
train.bat --epochs 100 --use-wandb --export-onnx
```

## Complete Setup Scripts

### Option 1: Automated Setup Script

```bash
# Run the comprehensive setup script
python scripts/setup_system.py

# This will:
# - Check your system configuration
# - Install all required dependencies
# - Create platform-specific training scripts
# - Verify the installation
# - Generate this deployment guide
```

### Option 2: Manual Installation

```bash
# 1. Install core dependencies
pip install -r requirements.txt

# 2. Verify installation
python scripts/install_dependencies.py

# 3. Test the setup
python scripts/train_detector.py --epochs 1 --batch-size 2 --experiment-name test
```

## Training Commands

### Basic Training
```bash
# Minimal training (1 epoch for testing)
python scripts/train_detector.py --epochs 1 --batch-size 2

# Standard training
python scripts/train_detector.py --epochs 100 --batch-size 16

# With Weights & Biases logging
python scripts/train_detector.py --epochs 100 --use-wandb

# With ONNX export
python scripts/train_detector.py --epochs 100 --export-onnx
```

### Advanced Training Options
```bash
# Large model with high batch size (requires powerful GPU)
python scripts/train_detector.py \
    --epochs 200 \
    --batch-size 32 \
    --model-size m \
    --learning-rate 0.001 \
    --use-wandb \
    --export-onnx

# CPU training (slower but works on any system)
python scripts/train_detector.py \
    --epochs 50 \
    --batch-size 4 \
    --device cpu

# Custom experiment name
python scripts/train_detector.py \
    --epochs 100 \
    --experiment-name "circuit_v2_$(date +%Y%m%d)"
```

## Platform-Specific Scripts

After running `python scripts/setup_system.py`, you'll have:

### Unix/Linux/macOS: `train.sh`
```bash
# Basic usage
./train.sh

# With parameters
./train.sh --epochs 100 --batch-size 16 --use-wandb --export-onnx

# Help
./train.sh --help
```

### Windows: `train.bat`
```cmd
REM Basic usage
train.bat

REM With parameters
train.bat --epochs 100 --batch-size 16 --use-wandb --export-onnx
```

### Cross-platform: `train.py`
```bash
# Works on all systems
python train.py --epochs 100 --use-wandb --export-onnx
```

## System Requirements

### Minimum Requirements
- **Python**: 3.9+
- **RAM**: 8GB
- **Storage**: 10GB free
- **OS**: Windows 10+, macOS 10.15+, Ubuntu 18.04+

### Recommended for GPU Training
- **GPU**: NVIDIA RTX 3060+ (6GB+ VRAM) or Apple Silicon M1+
- **RAM**: 16GB+
- **Storage**: SSD with 20GB+ free
- **CPU**: 6+ cores

### Batch Size Guidelines
| System | Recommended Batch Size |
|--------|----------------------|
| RTX 3060 (12GB) | 16-24 |
| RTX 3070 (8GB) | 12-16 |
| RTX 4090 (24GB) | 32-64 |
| Apple M1/M2 | 8-16 |
| CPU Only | 2-8 |

## Data Structure

Ensure your data follows this structure:
```
circuit2/
├── data/
│   └── processed/
│       ├── splits/
│       │   ├── train.json      # COCO format training annotations
│       │   ├── val.json        # COCO format validation annotations
│       │   └── test.json       # COCO format test annotations
│       └── organized/
│           └── images/         # All image files
│               ├── image1.jpg
│               ├── image2.jpg
│               └── ...
├── config/                     # Generated during training
├── models/                     # Exported models
├── runs/                       # Training logs
└── scripts/                    # Training scripts
```

## Troubleshooting

### Common Issues and Solutions

#### 1. "ModuleNotFoundError"
```bash
# Reinstall dependencies
python scripts/setup_system.py --force-reinstall

# Or manually
pip install --force-reinstall torch ultralytics
```

#### 2. "CUDA out of memory"
```bash
# Reduce batch size
python scripts/train_detector.py --batch-size 8

# Use smaller model
python scripts/train_detector.py --model-size n
```

#### 3. "No images found" error
- Check that images are in `data/processed/organized/images/`
- Verify image file names match those in the JSON files
- Ensure image formats are supported (jpg, jpeg, png)

#### 4. Slow training on Mac
```bash
# Ensure MPS is being used
python scripts/train_detector.py --device mps
```

#### 5. Permission errors (Linux/Mac)
```bash
chmod +x train.sh
chmod +x scripts/*.py
```

## Monitoring Training

### TensorBoard (Local)
```bash
# Start TensorBoard
tensorboard --logdir runs/

# Open browser to http://localhost:6006
```

### Weights & Biases (Cloud)
1. Create account at [wandb.ai](https://wandb.ai)
2. Get API key from account settings
3. Set environment variable:
   ```bash
   export WANDB_API_KEY="your_api_key_here"
   ```
4. Use `--use-wandb` flag when training

## Model Export and Inference

### Export to ONNX
```bash
# During training
python scripts/train_detector.py --export-onnx

# After training
python -c "
from ultralytics import YOLO
model = YOLO('circuitcli/experiment_name/weights/best.pt')
model.export(format='onnx')
"
```

### Run Inference
```bash
# Using trained model
python -c "
from ultralytics import YOLO
model = YOLO('circuitcli/experiment_name/weights/best.pt')
results = model('path/to/test/image.jpg')
results[0].show()
"
```

## Performance Optimization

### For Faster Training
1. **Use GPU**: NVIDIA GPU or Apple Silicon MPS
2. **Increase batch size**: Up to GPU memory limits
3. **Use SSD storage**: For faster data loading
4. **More CPU cores**: For data preprocessing

### For Better Accuracy
1. **More epochs**: 100-300 depending on dataset size
2. **Larger model**: YOLOv8s/m instead of YOLOv8n
3. **Data augmentation**: Enabled by default
4. **Learning rate scheduling**: Built into YOLOv8

## Environment Variables

### Optional Configuration
```bash
# Weights & Biases
export WANDB_API_KEY="your_key"
export WANDB_PROJECT="circuit-detection"

# CUDA settings
export CUDA_VISIBLE_DEVICES="0"  # Use specific GPU

# Disable WANDB if needed
export WANDB_DISABLED=true

# Increase data loading workers
export YOLO_WORKERS=8
```

## Docker Deployment (Advanced)

### Create Dockerfile
```dockerfile
FROM pytorch/pytorch:2.1.0-cuda11.8-devel-ubuntu20.04

WORKDIR /app
COPY . .

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -r requirements.txt

CMD ["python", "scripts/train_detector.py", "--epochs", "100"]
```

### Build and Run
```bash
# Build image
docker build -t circuitcli .

# Run training
docker run --gpus all -v $(pwd)/data:/app/data circuitcli
```

## Cloud Deployment

### Google Colab
```python
# Install in Colab cell
!git clone https://github.com/your-repo/circuit2.git
%cd circuit2
!python scripts/setup_system.py
!python scripts/train_detector.py --epochs 100 --use-wandb
```

### AWS/Azure/GCP
- Use GPU instances (p3.2xlarge, Standard_NC6s_v3, n1-standard-4 with GPU)
- Install CUDA drivers
- Follow Linux setup instructions

## Getting Help

### System Information
```bash
# Get detailed system info
python scripts/setup_system.py --system-info

# Verify installation
python scripts/setup_system.py --verify-only
```

### Debug Mode
```bash
# Run with verbose output
python scripts/train_detector.py --epochs 1 --batch-size 1 -v
```

### Common Commands Summary
```bash
# Setup system
python scripts/setup_system.py

# Quick test
python scripts/train_detector.py --epochs 1 --batch-size 2

# Full training
python scripts/train_detector.py --epochs 100 --use-wandb --export-onnx

# Platform-specific
./train.sh --epochs 100 --use-wandb  # Unix/Mac
train.bat --epochs 100 --use-wandb   # Windows
python train.py --epochs 100         # Cross-platform
```

---

**Need help?** Check the system requirements, verify your data structure, and try with smaller batch sizes first. 