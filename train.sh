#!/bin/bash
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
python scripts/train_detector.py \
    --epochs $EPOCHS \
    --batch-size $BATCH_SIZE \
    --model-size $MODEL_SIZE \
    --experiment-name $EXPERIMENT_NAME \
    $USE_WANDB \
    $EXPORT_ONNX \
    $DEVICE

echo "✅ Training completed successfully!"
