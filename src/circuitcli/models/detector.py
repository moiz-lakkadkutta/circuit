"""YOLOv8-based electrical component detector."""

import os
import torch
import torch.nn as nn
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

# Disable W&B by default to prevent automatic initialization
# This can be overridden later if W&B is explicitly requested
os.environ.setdefault("WANDB_MODE", "disabled")
os.environ.setdefault("WANDB_DISABLED", "true")

from ultralytics import YOLO
from ultralytics.utils.callbacks import add_integration_callbacks
import yaml
from rich.console import Console
from rich.progress import Progress, track
import wandb
from tensorboardX import SummaryWriter

from ..dataset.constants import ALL_COMPONENT_CLASSES, DATASET_CONFIG

console = Console()


class CircuitDetector:
    """YOLOv8-based detector for electrical circuit components."""
    
    def __init__(self, 
                 model_size: str = "n",
                 pretrained: bool = True,
                 num_classes: Optional[int] = None,
                 device: Optional[str] = None):
        """Initialize the circuit component detector.
        
        Args:
            model_size: YOLOv8 model size ('n', 's', 'm', 'l', 'x')
            pretrained: Whether to use pretrained COCO weights
            num_classes: Number of component classes (auto-detected if None)
            device: Device to run on ('cpu', 'cuda', 'mps', or None for auto)
        """
        self.model_size = model_size
        self.num_classes = num_classes or len(ALL_COMPONENT_CLASSES)
        self.device = device or self._get_best_device()
        self.model = None
        self.class_names = ALL_COMPONENT_CLASSES
        self.training_config = {}
        
        # Initialize model
        self._load_model(pretrained)
        
        console.print(f"🤖 Initialized CircuitDetector:")
        console.print(f"   Model: YOLOv8{model_size}")
        console.print(f"   Classes: {self.num_classes}")
        console.print(f"   Device: {self.device}")
        
    def _get_best_device(self) -> str:
        """Automatically select the best available device."""
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    
    def _load_model(self, pretrained: bool):
        """Load YOLOv8 model."""
        try:
            if pretrained:
                model_name = f"yolov8{self.model_size}.pt"
                console.print(f"📥 Loading pretrained {model_name}...")
            else:
                model_name = f"yolov8{self.model_size}.yaml"
                console.print(f"🏗️  Creating model from {model_name}...")
            
            self.model = YOLO(model_name)
            
            # Note: YOLOv8 will automatically adjust number of classes during training
            # based on the dataset configuration, so we don't need to manually modify it here
            console.print(f"✅ Model loaded successfully")
            console.print(f"   Model will be automatically configured for {self.num_classes} classes during training")
                
        except Exception as e:
            console.print(f"❌ Error loading model: {e}")
            raise
    
    def setup_training_config(self,
                            data_config_path: Path,
                            experiment_name: str = "circuit_detection",
                            epochs: int = 100,
                            batch_size: int = 16,
                            img_size: int = 640,
                            learning_rate: float = 0.01,
                            patience: int = 50,
                            save_period: int = 10,
                            use_wandb: bool = False,
                            use_tensorboard: bool = True) -> Dict[str, Any]:
        """Setup training configuration.
        
        Args:
            data_config_path: Path to data configuration YAML
            experiment_name: Name for the experiment
            epochs: Number of training epochs
            batch_size: Training batch size
            img_size: Input image size
            learning_rate: Initial learning rate
            patience: Early stopping patience
            save_period: Model checkpoint save period
            use_wandb: Whether to use Weights & Biases
            use_tensorboard: Whether to use TensorBoard
            
        Returns:
            Training configuration dictionary
        """
        self.training_config = {
            "data": str(data_config_path),
            "epochs": epochs,
            "batch": batch_size,
            "imgsz": img_size,
            "lr0": learning_rate,
            "patience": patience,
            "save_period": save_period,
            "project": "circuitcli",
            "name": experiment_name,
            "exist_ok": True,
            "pretrained": True,
            "optimizer": "AdamW",
            "verbose": True,
            "seed": DATASET_CONFIG["random_seed"],
            "deterministic": True,
            "single_cls": False,
            "rect": False,
            "cos_lr": True,
            "close_mosaic": 10,
            "resume": False,
            "amp": True,  # Automatic Mixed Precision
            "fraction": 1.0,
            "profile": False,
            "freeze": None,
            "multi_scale": True,
            "overlap_mask": True,
            "mask_ratio": 4,
            "dropout": 0.0,
            "val": True,
            "split": "val",
            "save": True,
            "save_json": True,
            "save_hybrid": False,
            "conf": 0.001,
            "iou": 0.7,
            "max_det": 300,
            "half": False,
            "dnn": False,
            "plots": True,
            "device": self.device
        }
        
        # Setup experiment tracking
        if use_wandb:
            # Re-enable W&B if explicitly requested
            os.environ.pop("WANDB_MODE", None)
            os.environ.pop("WANDB_DISABLED", None)
            self._setup_wandb(experiment_name)
        else:
            # Ensure W&B remains disabled
            os.environ["WANDB_MODE"] = "disabled"
            os.environ["WANDB_DISABLED"] = "true"
            console.print("🚫 Weights & Biases disabled")
            
        if use_tensorboard:
            self._setup_tensorboard(experiment_name)
            
        console.print(f"⚙️  Training config setup for {experiment_name}")
        return self.training_config
    
    def _setup_wandb(self, experiment_name: str):
        """Setup Weights & Biases integration."""
        try:
            wandb.init(
                project="circuitcli-detection",
                name=experiment_name,
                config=self.training_config,
                job_type="training",
                tags=["yolov8", "electrical-components", "circuit-detection"]
            )
            console.print("📊 Weights & Biases initialized")
        except Exception as e:
            console.print(f"⚠️  Warning: W&B setup failed: {e}")
    
    def _setup_tensorboard(self, experiment_name: str):
        """Setup TensorBoard integration."""
        try:
            log_dir = Path(f"runs/{experiment_name}")
            log_dir.mkdir(parents=True, exist_ok=True)
            self.tb_writer = SummaryWriter(log_dir)
            console.print(f"📈 TensorBoard logs: {log_dir}")
        except Exception as e:
            console.print(f"⚠️  Warning: TensorBoard setup failed: {e}")
    
    def load_class_info_from_config(self, config_path: Path) -> bool:
        """Load class information from YOLOv8 config file.
        
        Args:
            config_path: Path to YOLOv8 config YAML
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            self.num_classes = config.get('nc', 80)
            names_dict = config.get('names', {})
            
            # Convert names dict to list
            if isinstance(names_dict, dict):
                self.class_names = [names_dict.get(i, f'class_{i}') for i in range(self.num_classes)]
            else:
                self.class_names = names_dict if names_dict else [f'class_{i}' for i in range(self.num_classes)]
            
            console.print(f"📚 Loaded class info from config:")
            console.print(f"   Classes: {self.num_classes}")
            console.print(f"   Names: {self.class_names[:5]}{'...' if len(self.class_names) > 5 else ''}")
            
            return True
            
        except Exception as e:
            console.print(f"❌ Error loading class info: {e}")
            return False
    
    def train(self, resume: bool = False, resume_path: Optional[Path] = None) -> Dict[str, Any]:
        """Train the detector model.
        
        Args:
            resume: Whether to resume training from checkpoint
            resume_path: Path to checkpoint for resuming
            
        Returns:
            Training results dictionary
        """
        if not self.training_config:
            raise ValueError("Training config not set. Call setup_training_config() first.")
        
        console.print("🚀 Starting YOLOv8 training...")
        console.print(f"📊 Training configuration:")
        for key, value in self.training_config.items():
            if key not in ['device']:  # Skip verbose items
                console.print(f"   {key}: {value}")
        
        try:
            # Handle resume
            if resume and resume_path:
                self.training_config["resume"] = str(resume_path)
                console.print(f"🔄 Resuming from: {resume_path}")
            
            # Start training
            results = self.model.train(**self.training_config)
            
            console.print("✅ Training completed successfully!")
            
            # Log final metrics
            if hasattr(results, 'results_dict'):
                self._log_final_metrics(results.results_dict)
            
            return results
            
        except Exception as e:
            console.print(f"❌ Training failed: {e}")
            raise
    
    def _log_final_metrics(self, results_dict: Dict[str, Any]):
        """Log final training metrics."""
        metrics_to_log = [
            'metrics/mAP50(B)', 'metrics/mAP50-95(B)',
            'metrics/precision(B)', 'metrics/recall(B)'
        ]
        
        console.print("\n📊 Final Training Metrics:")
        for metric in metrics_to_log:
            if metric in results_dict:
                value = results_dict[metric]
                console.print(f"   {metric}: {value:.4f}")
                
                # Log to W&B if available
                if wandb.run:
                    wandb.log({f"final_{metric}": value})
    
    def validate(self, data_config_path: Path, checkpoint_path: Optional[Path] = None) -> Dict[str, Any]:
        """Validate the model on test set.
        
        Args:
            data_config_path: Path to data configuration
            checkpoint_path: Path to model checkpoint (uses best if None)
            
        Returns:
            Validation results
        """
        try:
            if checkpoint_path:
                model = YOLO(str(checkpoint_path))
            else:
                model = self.model
            
            console.print("🔍 Running validation...")
            results = model.val(
                data=str(data_config_path),
                split='test',
                save_json=True,
                save_hybrid=True,
                plots=True,
                verbose=True
            )
            
            console.print("✅ Validation completed!")
            return results
            
        except Exception as e:
            console.print(f"❌ Validation failed: {e}")
            raise
    
    def export_onnx(self, 
                   checkpoint_path: Path,
                   output_path: Path,
                   input_size: Tuple[int, int] = (640, 640),
                   optimize: bool = True,
                   simplify: bool = True) -> bool:
        """Export model to ONNX format.
        
        Args:
            checkpoint_path: Path to trained model checkpoint
            output_path: Output path for ONNX model
            input_size: Input image size (height, width)
            optimize: Whether to optimize the model
            simplify: Whether to simplify the model
            
        Returns:
            True if successful, False otherwise
        """
        try:
            console.print("📦 Exporting model to ONNX...")
            
            # Load trained model
            model = YOLO(str(checkpoint_path))
            
            # Export to ONNX
            model.export(
                format='onnx',
                imgsz=input_size,
                optimize=optimize,
                simplify=simplify,
                dynamic=False,
                opset=12
            )
            
            # Move to desired location if needed
            exported_path = checkpoint_path.parent / (checkpoint_path.stem + '.onnx')
            if exported_path != output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                exported_path.rename(output_path)
            
            console.print(f"✅ ONNX model exported: {output_path}")
            
            # Verify the exported model
            self._verify_onnx_export(output_path, input_size)
            
            return True
            
        except Exception as e:
            console.print(f"❌ ONNX export failed: {e}")
            return False
    
    def _verify_onnx_export(self, onnx_path: Path, input_size: Tuple[int, int]):
        """Verify ONNX model export."""
        try:
            import onnx
            import onnxruntime as ort
            
            # Load and check ONNX model
            onnx_model = onnx.load(str(onnx_path))
            onnx.checker.check_model(onnx_model)
            
            # Test inference
            ort_session = ort.InferenceSession(str(onnx_path))
            
            # Create dummy input
            dummy_input = np.random.rand(1, 3, *input_size).astype(np.float32)
            
            # Run inference
            outputs = ort_session.run(None, {"images": dummy_input})
            
            console.print(f"✅ ONNX model verified successfully")
            console.print(f"   Input shape: {dummy_input.shape}")
            console.print(f"   Output shapes: {[out.shape for out in outputs]}")
            
        except ImportError:
            console.print("⚠️  ONNX verification skipped (onnx/onnxruntime not installed)")
        except Exception as e:
            console.print(f"⚠️  ONNX verification failed: {e}")
    
    def predict(self, 
               image_path: Path,
               checkpoint_path: Optional[Path] = None,
               conf_threshold: float = 0.25,
               iou_threshold: float = 0.45,
               save_results: bool = True) -> Dict[str, Any]:
        """Run inference on a single image.
        
        Args:
            image_path: Path to input image
            checkpoint_path: Path to model checkpoint
            conf_threshold: Confidence threshold
            iou_threshold: IoU threshold for NMS
            save_results: Whether to save visualization
            
        Returns:
            Detection results
        """
        try:
            if checkpoint_path:
                model = YOLO(str(checkpoint_path))
            else:
                model = self.model
            
            results = model.predict(
                source=str(image_path),
                conf=conf_threshold,
                iou=iou_threshold,
                save=save_results,
                save_txt=True,
                save_conf=True,
                project="runs/predict",
                name="circuit_detection"
            )
            
            return results[0] if results else None
            
        except Exception as e:
            console.print(f"❌ Prediction failed: {e}")
            raise
    
    def benchmark_performance(self, 
                            checkpoint_path: Path,
                            test_images_dir: Path,
                            num_samples: int = 100) -> Dict[str, float]:
        """Benchmark model performance (speed and accuracy).
        
        Args:
            checkpoint_path: Path to model checkpoint
            test_images_dir: Directory with test images
            num_samples: Number of images to test
            
        Returns:
            Performance metrics
        """
        try:
            import time
            from PIL import Image
            
            model = YOLO(str(checkpoint_path))
            
            # Get test images
            test_images = list(test_images_dir.glob("*.jpg"))[:num_samples]
            
            if not test_images:
                raise ValueError(f"No test images found in {test_images_dir}")
            
            console.print(f"🏁 Benchmarking performance on {len(test_images)} images...")
            
            inference_times = []
            
            with Progress() as progress:
                task = progress.add_task("Benchmarking...", total=len(test_images))
                
                for img_path in test_images:
                    # Measure inference time
                    start_time = time.time()
                    _ = model.predict(
                        source=str(img_path),
                        conf=0.25,
                        iou=0.45,
                        save=False,
                        verbose=False
                    )
                    end_time = time.time()
                    
                    inference_times.append(end_time - start_time)
                    progress.advance(task)
            
            # Calculate metrics
            avg_inference_time = np.mean(inference_times)
            fps = 1.0 / avg_inference_time
            
            performance_metrics = {
                "avg_inference_time_ms": avg_inference_time * 1000,
                "fps": fps,
                "min_inference_time_ms": np.min(inference_times) * 1000,
                "max_inference_time_ms": np.max(inference_times) * 1000,
                "std_inference_time_ms": np.std(inference_times) * 1000
            }
            
            console.print("\n🏁 Performance Benchmark Results:")
            for metric, value in performance_metrics.items():
                console.print(f"   {metric}: {value:.2f}")
            
            return performance_metrics
            
        except Exception as e:
            console.print(f"❌ Benchmarking failed: {e}")
            raise 