#!/usr/bin/env python3
"""Training script for YOLOv8 electrical component detector."""

import sys
import argparse
from pathlib import Path
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from circuitcli.models.detector import CircuitDetector
from circuitcli.models.model_export import ModelExporter
from circuitcli.models.yolo_dataset_converter import convert_coco_to_yolo_format
from rich.console import Console

console = Console()


def setup_yolo_dataset(splits_dir: Path, images_dir: Path, yolo_dataset_dir: Path, config_path: Path) -> bool:
    """Setup YOLOv8 dataset and configuration."""
    train_json = splits_dir / "train.json"
    val_json = splits_dir / "val.json"
    test_json = splits_dir / "test.json"
    
    if not all([train_json.exists(), val_json.exists(), test_json.exists()]):
        console.print("❌ Missing dataset splits!")
        return False
    
    # Convert COCO to YOLOv8 format
    return convert_coco_to_yolo_format(
        train_json, val_json, test_json, images_dir, yolo_dataset_dir, config_path
    )


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv8 electrical component detector")
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"),
                       help="Directory containing processed dataset")
    parser.add_argument("--model-size", choices=["n", "s", "m", "l", "x"], default="n",
                       help="YOLOv8 model size")
    parser.add_argument("--epochs", type=int, default=100,
                       help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16,
                       help="Training batch size")
    parser.add_argument("--img-size", type=int, default=640,
                       help="Input image size")
    parser.add_argument("--learning-rate", type=float, default=0.01,
                       help="Initial learning rate")
    parser.add_argument("--patience", type=int, default=50,
                       help="Early stopping patience")
    parser.add_argument("--experiment-name", type=str, default="circuit_detection_v1",
                       help="Experiment name")
    parser.add_argument("--use-wandb", action="store_true",
                       help="Use Weights & Biases for experiment tracking")
    parser.add_argument("--resume", type=Path,
                       help="Resume training from checkpoint")
    parser.add_argument("--export-onnx", action="store_true",
                       help="Export best model to ONNX after training")
    parser.add_argument("--device", type=str,
                       help="Device to use (cpu, cuda, mps)")
    
    args = parser.parse_args()
    
    # Setup paths
    data_dir = Path(args.data_dir)
    splits_dir = data_dir / "splits"
    images_dir = data_dir / "organized" / "images"
    yolo_dataset_dir = data_dir / "yolo_format"
    
    if not splits_dir.exists():
        console.print(f"❌ Splits directory not found: {splits_dir}")
        return 1
    
    if not images_dir.exists():
        console.print(f"❌ Images directory not found: {images_dir}")
        return 1
    
    console.print("🚀 CircuitCLI YOLOv8 Training")
    console.print("=" * 50)
    console.print(f"📁 Data directory: {data_dir}")
    console.print(f"🤖 Model size: YOLOv8{args.model_size}")
    console.print(f"📊 Epochs: {args.epochs}")
    console.print(f"🎯 Batch size: {args.batch_size}")
    console.print(f"📐 Image size: {args.img_size}")
    console.print(f"📈 Learning rate: {args.learning_rate}")
    
    try:
        # 1. Setup YOLOv8 dataset
        console.print("\n📋 Step 1: Converting COCO to YOLOv8 format...")
        data_config_path = Path("config/yolo_data.yaml")
        if not setup_yolo_dataset(splits_dir, images_dir, yolo_dataset_dir, data_config_path):
            return 1
        
        # 2. Initialize detector
        console.print("\n🤖 Step 2: Initializing detector...")
        detector = CircuitDetector(
            model_size=args.model_size,
            pretrained=True,
            device=args.device
        )
        
        # Load class information from the config
        detector.load_class_info_from_config(data_config_path)
        
        # 3. Setup training configuration
        console.print("\n⚙️  Step 3: Setting up training configuration...")
        console.print(f"   W&B enabled: {args.use_wandb}")
        console.print(f"   TensorBoard enabled: True")
        
        training_config = detector.setup_training_config(
            data_config_path=data_config_path,
            experiment_name=args.experiment_name,
            epochs=args.epochs,
            batch_size=args.batch_size,
            img_size=args.img_size,
            learning_rate=args.learning_rate,
            patience=args.patience,
            use_wandb=args.use_wandb,
            use_tensorboard=True
        )
        
        # 4. Train model
        console.print("\n🏋️  Step 4: Starting training...")
        results = detector.train(
            resume=args.resume is not None,
            resume_path=args.resume
        )
        
        # 5. Validate model
        console.print("\n🔍 Step 5: Validating model...")
        val_results = detector.validate(data_config_path)
        
        # 6. Export to ONNX if requested
        if args.export_onnx:
            console.print("\n📦 Step 6: Exporting to ONNX...")
            
            # Find best checkpoint
            best_checkpoint = Path(f"circuitcli/{args.experiment_name}/weights/best.pt")
            if best_checkpoint.exists():
                onnx_output = Path(f"models/{args.experiment_name}_best.onnx")
                
                if detector.export_onnx(best_checkpoint, onnx_output):
                    console.print(f"✅ ONNX model exported: {onnx_output}")
                    
                    # Benchmark performance
                    exporter = ModelExporter()
                    benchmark_results = exporter.benchmark_onnx_model(
                        onnx_output, (1, 3, args.img_size, args.img_size)
                    )
                    
                    console.print(f"🏁 ONNX Performance:")
                    console.print(f"   Inference time: {benchmark_results.get('avg_inference_time_ms', 0):.2f}ms")
                    console.print(f"   FPS: {benchmark_results.get('fps', 0):.2f}")
                else:
                    console.print("❌ ONNX export failed")
            else:
                console.print(f"❌ Best checkpoint not found: {best_checkpoint}")
        
        # 7. Training summary
        console.print("\n🎉 Training completed successfully!")
        console.print(f"📊 Experiment: {args.experiment_name}")
        console.print(f"💾 Checkpoints: circuitcli/{args.experiment_name}/weights/")
        console.print(f"📈 Logs: runs/{args.experiment_name}/")
        
        if args.use_wandb:
            console.print(f"🌐 W&B Dashboard: https://wandb.ai/")
        
        return 0
        
    except Exception as e:
        console.print(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 