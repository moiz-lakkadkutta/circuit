#!/usr/bin/env python3
"""Test script for trained YOLOv8 electrical component detector."""

import sys
import argparse
from pathlib import Path
import json
from typing import Dict, List, Any
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from circuitcli.models.detector import CircuitDetector
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
import numpy as np

console = Console()


def test_single_image(model_path: Path, image_path: Path, 
                     conf_threshold: float = 0.25, 
                     iou_threshold: float = 0.45,
                     save_visualization: bool = True) -> Dict[str, Any]:
    """Test model on a single image."""
    console.print(f"🔍 Testing model on: {image_path}")
    
    detector = CircuitDetector()
    
    # Run prediction
    start_time = time.time()
    results = detector.predict(
        image_path=image_path,
        checkpoint_path=model_path,
        conf_threshold=conf_threshold,
        iou_threshold=iou_threshold,
        save_results=save_visualization
    )
    inference_time = time.time() - start_time
    
    if results:
        # Extract detection information
        boxes = results.boxes
        num_detections = len(boxes) if boxes is not None else 0
        
        detection_info = {
            "image_path": str(image_path),
            "num_detections": num_detections,
            "inference_time_ms": inference_time * 1000,
            "detections": []
        }
        
        if boxes is not None:
            for i, box in enumerate(boxes):
                # Get class name if available
                class_id = int(box.cls.item()) if box.cls is not None else -1
                confidence = float(box.conf.item()) if box.conf is not None else 0.0
                bbox = box.xyxy.cpu().numpy().tolist()[0] if box.xyxy is not None else []
                
                detection_info["detections"].append({
                    "class_id": class_id,
                    "confidence": confidence,
                    "bbox": bbox  # [x1, y1, x2, y2]
                })
        
        # Print results
        console.print(f"✅ Found {num_detections} detections")
        console.print(f"⏱️  Inference time: {inference_time*1000:.2f}ms")
        
        if save_visualization:
            console.print(f"📁 Visualization saved to: runs/predict/circuit_detection/")
        
        return detection_info
    else:
        console.print("❌ No detections found")
        return {
            "image_path": str(image_path),
            "num_detections": 0,
            "inference_time_ms": inference_time * 1000,
            "detections": []
        }


def test_batch_images(model_path: Path, images_dir: Path,
                     conf_threshold: float = 0.25,
                     iou_threshold: float = 0.45,
                     max_images: int = None) -> List[Dict[str, Any]]:
    """Test model on multiple images."""
    console.print(f"🔍 Testing model on images in: {images_dir}")
    
    # Find all image files
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
    image_files = []
    for ext in image_extensions:
        image_files.extend(list(images_dir.glob(f"*{ext}")))
        image_files.extend(list(images_dir.glob(f"*{ext.upper()}")))
    
    if max_images:
        image_files = image_files[:max_images]
    
    if not image_files:
        console.print(f"❌ No images found in {images_dir}")
        return []
    
    console.print(f"📊 Found {len(image_files)} images to test")
    
    detector = CircuitDetector()
    results = []
    
    with Progress() as progress:
        task = progress.add_task("Testing images...", total=len(image_files))
        
        for image_path in image_files:
            try:
                # Run prediction
                start_time = time.time()
                prediction = detector.predict(
                    image_path=image_path,
                    checkpoint_path=model_path,
                    conf_threshold=conf_threshold,
                    iou_threshold=iou_threshold,
                    save_results=False  # Don't save individual results for batch
                )
                inference_time = time.time() - start_time
                
                # Extract results
                num_detections = len(prediction.boxes) if prediction and prediction.boxes is not None else 0
                
                results.append({
                    "image_path": str(image_path),
                    "num_detections": num_detections,
                    "inference_time_ms": inference_time * 1000
                })
                
            except Exception as e:
                console.print(f"❌ Failed to process {image_path}: {e}")
                results.append({
                    "image_path": str(image_path),
                    "num_detections": 0,
                    "inference_time_ms": 0,
                    "error": str(e)
                })
            
            progress.advance(task)
    
    return results


def benchmark_model(model_path: Path, test_images_dir: Path, 
                   num_samples: int = 100) -> Dict[str, float]:
    """Benchmark model performance."""
    console.print(f"🏁 Benchmarking model performance...")
    
    detector = CircuitDetector()
    
    try:
        metrics = detector.benchmark_performance(
            checkpoint_path=model_path,
            test_images_dir=test_images_dir,
            num_samples=num_samples
        )
        return metrics
    except Exception as e:
        console.print(f"❌ Benchmarking failed: {e}")
        return {}


def validate_model_on_test_set(model_path: Path, data_config_path: Path) -> Dict[str, Any]:
    """Validate model on test set using YOLOv8's built-in validation."""
    console.print("🔍 Validating model on test set...")
    
    detector = CircuitDetector()
    
    try:
        # Load the trained model
        from ultralytics import YOLO
        model = YOLO(str(model_path))
        
        # Run validation
        results = model.val(
            data=str(data_config_path),
            split='test',
            save_json=True,
            save_hybrid=True,
            plots=True,
            verbose=True
        )
        
        # Extract metrics
        metrics = {
            "map50": float(results.box.map50) if hasattr(results.box, 'map50') else 0.0,
            "map50_95": float(results.box.map) if hasattr(results.box, 'map') else 0.0,
            "precision": float(results.box.mp) if hasattr(results.box, 'mp') else 0.0,
            "recall": float(results.box.mr) if hasattr(results.box, 'mr') else 0.0,
            "fitness": float(results.fitness) if hasattr(results, 'fitness') else 0.0
        }
        
        console.print("✅ Validation completed!")
        console.print(f"📊 mAP@50: {metrics['map50']:.3f}")
        console.print(f"📊 mAP@50-95: {metrics['map50_95']:.3f}")
        console.print(f"📊 Precision: {metrics['precision']:.3f}")
        console.print(f"📊 Recall: {metrics['recall']:.3f}")
        
        return metrics
        
    except Exception as e:
        console.print(f"❌ Validation failed: {e}")
        return {}


def print_summary_table(results: List[Dict[str, Any]]):
    """Print a summary table of test results."""
    if not results:
        return
    
    table = Table(title="Model Testing Summary")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")
    
    # Calculate statistics
    total_images = len(results)
    successful_predictions = len([r for r in results if 'error' not in r])
    total_detections = sum(r.get('num_detections', 0) for r in results)
    inference_times = [r.get('inference_time_ms', 0) for r in results if 'error' not in r]
    
    # Add rows
    table.add_row("Total Images", str(total_images))
    table.add_row("Successful Predictions", str(successful_predictions))
    table.add_row("Total Detections", str(total_detections))
    table.add_row("Avg Detections per Image", f"{total_detections/total_images:.2f}")
    
    if inference_times:
        table.add_row("Avg Inference Time", f"{np.mean(inference_times):.2f}ms")
        table.add_row("Min Inference Time", f"{np.min(inference_times):.2f}ms")
        table.add_row("Max Inference Time", f"{np.max(inference_times):.2f}ms")
        table.add_row("Inference FPS", f"{1000/np.mean(inference_times):.2f}")
    
    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="Test trained YOLOv8 electrical component detector")
    parser.add_argument("--model-path", type=Path, required=True,
                       help="Path to trained model checkpoint (best.pt)")
    parser.add_argument("--test-type", choices=["single", "batch", "benchmark", "validate", "all"],
                       default="all", help="Type of test to run")
    
    # Single image test options
    parser.add_argument("--image-path", type=Path,
                       help="Path to single image for testing")
    
    # Batch test options
    parser.add_argument("--images-dir", type=Path,
                       help="Directory containing test images")
    parser.add_argument("--max-images", type=int,
                       help="Maximum number of images to test (for batch testing)")
    
    # Benchmark options
    parser.add_argument("--benchmark-samples", type=int, default=100,
                       help="Number of samples for benchmarking")
    
    # Validation options
    parser.add_argument("--data-config", type=Path, default=Path("config/yolo_data.yaml"),
                       help="Path to YOLO data configuration file")
    
    # Common options
    parser.add_argument("--conf-threshold", type=float, default=0.25,
                       help="Confidence threshold for detections")
    parser.add_argument("--iou-threshold", type=float, default=0.45,
                       help="IoU threshold for NMS")
    parser.add_argument("--save-results", action="store_true",
                       help="Save visualization results")
    parser.add_argument("--output-file", type=Path,
                       help="Save test results to JSON file")
    
    args = parser.parse_args()
    
    # Validate model path
    if not args.model_path.exists():
        console.print(f"❌ Model file not found: {args.model_path}")
        return 1
    
    console.print("🧪 CircuitCLI Model Testing")
    console.print("=" * 50)
    console.print(f"🤖 Model: {args.model_path}")
    console.print(f"🎯 Confidence threshold: {args.conf_threshold}")
    console.print(f"🔄 IoU threshold: {args.iou_threshold}")
    
    all_results = {}
    
    try:
        # Single image test
        if args.test_type in ["single", "all"] and args.image_path:
            console.print("\n📸 Single Image Test")
            console.print("-" * 30)
            result = test_single_image(
                args.model_path, args.image_path,
                args.conf_threshold, args.iou_threshold,
                args.save_results
            )
            all_results["single_image"] = result
        
        # Batch test
        if args.test_type in ["batch", "all"] and args.images_dir:
            console.print("\n📚 Batch Image Test")
            console.print("-" * 30)
            results = test_batch_images(
                args.model_path, args.images_dir,
                args.conf_threshold, args.iou_threshold,
                args.max_images
            )
            all_results["batch_images"] = results
            print_summary_table(results)
        
        # Benchmark test
        if args.test_type in ["benchmark", "all"] and args.images_dir:
            console.print("\n🏁 Performance Benchmark")
            console.print("-" * 30)
            benchmark_results = benchmark_model(
                args.model_path, args.images_dir,
                args.benchmark_samples
            )
            all_results["benchmark"] = benchmark_results
        
        # Validation test
        if args.test_type in ["validate", "all"]:
            console.print("\n🔍 Model Validation")
            console.print("-" * 30)
            if args.data_config.exists():
                validation_results = validate_model_on_test_set(
                    args.model_path, args.data_config
                )
                all_results["validation"] = validation_results
            else:
                console.print(f"❌ Data config not found: {args.data_config}")
        
        # Save results to file
        if args.output_file:
            with open(args.output_file, 'w') as f:
                json.dump(all_results, f, indent=2, default=str)
            console.print(f"\n💾 Results saved to: {args.output_file}")
        
        console.print("\n🎉 Testing completed successfully!")
        return 0
        
    except Exception as e:
        console.print(f"❌ Testing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 