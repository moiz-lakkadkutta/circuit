# CircuitCLI Deployment Guide

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
venv\Scripts\activate

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

Current system detected: **Darwin**
Python version: **3.10.11**
GPU support: **mps (Apple Silicon)**
