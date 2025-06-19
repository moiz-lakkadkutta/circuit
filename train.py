#!/usr/bin/env python3
"""
Cross-platform training launcher for CircuitCLI.
This script provides a unified interface across different operating systems.
"""

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
        print("\n⚠️  Training interrupted by user")
        return 1

if __name__ == "__main__":
    sys.exit(main())
