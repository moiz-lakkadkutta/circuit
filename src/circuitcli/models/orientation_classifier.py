"""Orientation classifier for rotated electrical components."""

import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from PIL import Image
import torchvision.transforms as transforms
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
from rich.console import Console
from rich.progress import Progress, track
import wandb
from tensorboardX import SummaryWriter
from torch.utils.data import Dataset, DataLoader
import json

console = Console()


class ComponentCropDataset(Dataset):
    """Dataset for component orientation classification."""
    
    def __init__(self, 
                 crops_dir: Path,
                 annotations_file: Path,
                 transform: Optional[transforms.Compose] = None,
                 augment: bool = False):
        """Initialize the dataset.
        
        Args:
            crops_dir: Directory containing component crops
            annotations_file: JSON file with crop annotations
            transform: Image transformations
            augment: Whether to apply augmentations
        """
        self.crops_dir = Path(crops_dir)
        self.transform = transform
        self.augment = augment
        
        # Load annotations
        with open(annotations_file, 'r') as f:
            self.annotations = json.load(f)
        
        # Define orientation classes
        self.orientation_classes = {
            0: "0°",     # No rotation
            1: "90°",    # 90 degrees clockwise
            2: "180°",   # 180 degrees
            3: "270°"    # 270 degrees clockwise (90° counter-clockwise)
        }
        
        console.print(f"📁 Loaded {len(self.annotations)} orientation samples")
        
    def __len__(self):
        return len(self.annotations)
    
    def __getitem__(self, idx):
        """Get dataset item."""
        annotation = self.annotations[idx]
        
        # Load image
        image_path = self.crops_dir / annotation['filename']
        image = Image.open(image_path).convert('RGB')
        
        # Get orientation label
        orientation_label = annotation['orientation']  # 0, 1, 2, or 3
        
        # Apply transforms
        if self.transform:
            image = self.transform(image)
        
        return image, orientation_label


class OrientationClassifier:
    """Lightweight CNN for classifying component orientations."""
    
    def __init__(self, 
                 num_classes: int = 4,
                 pretrained: bool = True,
                 device: Optional[str] = None):
        """Initialize the orientation classifier.
        
        Args:
            num_classes: Number of orientation classes (default: 4 for 0°, 90°, 180°, 270°)
            pretrained: Whether to use pretrained weights
            device: Device to run on ('cpu', 'cuda', 'mps', or None for auto)
        """
        self.num_classes = num_classes
        self.device = device or self._get_best_device()
        self.model = None
        self.optimizer = None
        self.scheduler = None
        self.criterion = nn.CrossEntropyLoss()
        
        # Initialize model
        self._build_model(pretrained)
        
        # Data transforms
        self.train_transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(degrees=5),  # Small rotation for augmentation
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        self.val_transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        console.print(f"🧭 Initialized OrientationClassifier:")
        console.print(f"   Classes: {num_classes}")
        console.print(f"   Device: {self.device}")
        
    def _get_best_device(self) -> str:
        """Automatically select the best available device."""
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    
    def _build_model(self, pretrained: bool):
        """Build the orientation classification model."""
        try:
            # Use EfficientNet-B0 as backbone (lightweight and efficient)
            if pretrained:
                weights = EfficientNet_B0_Weights.IMAGENET1K_V1
                self.model = efficientnet_b0(weights=weights)
            else:
                self.model = efficientnet_b0(weights=None)
            
            # Replace classifier head
            in_features = self.model.classifier[1].in_features
            self.model.classifier = nn.Sequential(
                nn.Dropout(p=0.2),
                nn.Linear(in_features, 128),
                nn.ReLU(),
                nn.Dropout(p=0.2),
                nn.Linear(128, self.num_classes)
            )
            
            # Move to device
            self.model = self.model.to(self.device)
            
            console.print("✅ Model built successfully")
            
        except Exception as e:
            console.print(f"❌ Error building model: {e}")
            raise
    
    def setup_training(self,
                      learning_rate: float = 0.001,
                      weight_decay: float = 1e-4,
                      scheduler_step_size: int = 10,
                      scheduler_gamma: float = 0.1):
        """Setup training components.
        
        Args:
            learning_rate: Initial learning rate
            weight_decay: Weight decay for regularization
            scheduler_step_size: Step size for learning rate scheduler
            scheduler_gamma: Gamma for learning rate scheduler
        """
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )
        
        self.scheduler = torch.optim.lr_scheduler.StepLR(
            self.optimizer,
            step_size=scheduler_step_size,
            gamma=scheduler_gamma
        )
        
        console.print("⚙️  Training setup completed")
    
    def create_dataloaders(self,
                          train_crops_dir: Path,
                          val_crops_dir: Path,
                          train_annotations: Path,
                          val_annotations: Path,
                          batch_size: int = 32,
                          num_workers: int = 4) -> Tuple[DataLoader, DataLoader]:
        """Create data loaders for training and validation.
        
        Args:
            train_crops_dir: Directory with training component crops
            val_crops_dir: Directory with validation component crops
            train_annotations: Training annotations JSON file
            val_annotations: Validation annotations JSON file
            batch_size: Batch size for training
            num_workers: Number of worker processes
            
        Returns:
            Tuple of (train_loader, val_loader)
        """
        # Create datasets
        train_dataset = ComponentCropDataset(
            train_crops_dir, train_annotations, 
            transform=self.train_transform, augment=True
        )
        
        val_dataset = ComponentCropDataset(
            val_crops_dir, val_annotations,
            transform=self.val_transform, augment=False
        )
        
        # Create data loaders
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=num_workers,
            pin_memory=True
        )
        
        val_loader = DataLoader(
            val_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=num_workers,
            pin_memory=True
        )
        
        console.print(f"📊 Created data loaders:")
        console.print(f"   Train: {len(train_dataset)} samples, {len(train_loader)} batches")
        console.print(f"   Val: {len(val_dataset)} samples, {len(val_loader)} batches")
        
        return train_loader, val_loader
    
    def train_epoch(self, train_loader: DataLoader) -> Dict[str, float]:
        """Train for one epoch.
        
        Args:
            train_loader: Training data loader
            
        Returns:
            Training metrics for the epoch
        """
        self.model.train()
        
        total_loss = 0.0
        correct_predictions = 0
        total_samples = 0
        
        with Progress() as progress:
            task = progress.add_task("Training...", total=len(train_loader))
            
            for batch_idx, (images, labels) in enumerate(train_loader):
                # Move to device
                images = images.to(self.device)
                labels = labels.to(self.device)
                
                # Forward pass
                self.optimizer.zero_grad()
                outputs = self.model(images)
                loss = self.criterion(outputs, labels)
                
                # Backward pass
                loss.backward()
                self.optimizer.step()
                
                # Statistics
                total_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total_samples += labels.size(0)
                correct_predictions += (predicted == labels).sum().item()
                
                progress.advance(task)
        
        # Calculate metrics
        avg_loss = total_loss / len(train_loader)
        accuracy = 100.0 * correct_predictions / total_samples
        
        return {
            "loss": avg_loss,
            "accuracy": accuracy
        }
    
    def validate_epoch(self, val_loader: DataLoader) -> Dict[str, float]:
        """Validate for one epoch.
        
        Args:
            val_loader: Validation data loader
            
        Returns:
            Validation metrics for the epoch
        """
        self.model.eval()
        
        total_loss = 0.0
        correct_predictions = 0
        total_samples = 0
        
        with torch.no_grad():
            with Progress() as progress:
                task = progress.add_task("Validating...", total=len(val_loader))
                
                for images, labels in val_loader:
                    # Move to device
                    images = images.to(self.device)
                    labels = labels.to(self.device)
                    
                    # Forward pass
                    outputs = self.model(images)
                    loss = self.criterion(outputs, labels)
                    
                    # Statistics
                    total_loss += loss.item()
                    _, predicted = torch.max(outputs.data, 1)
                    total_samples += labels.size(0)
                    correct_predictions += (predicted == labels).sum().item()
                    
                    progress.advance(task)
        
        # Calculate metrics
        avg_loss = total_loss / len(val_loader)
        accuracy = 100.0 * correct_predictions / total_samples
        
        return {
            "loss": avg_loss,
            "accuracy": accuracy
        }
    
    def train(self,
             train_loader: DataLoader,
             val_loader: DataLoader,
             epochs: int = 50,
             save_dir: Path = Path("models/orientation"),
             experiment_name: str = "orientation_classification",
             use_wandb: bool = True) -> Dict[str, List[float]]:
        """Train the orientation classifier.
        
        Args:
            train_loader: Training data loader
            val_loader: Validation data loader
            epochs: Number of training epochs
            save_dir: Directory to save model checkpoints
            experiment_name: Name for the experiment
            use_wandb: Whether to use Weights & Biases
            
        Returns:
            Training history
        """
        if not self.optimizer:
            raise ValueError("Training not setup. Call setup_training() first.")
        
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup experiment tracking
        if use_wandb:
            wandb.init(
                project="circuitcli-orientation",
                name=experiment_name,
                config={
                    "epochs": epochs,
                    "batch_size": train_loader.batch_size,
                    "learning_rate": self.optimizer.param_groups[0]['lr'],
                    "num_classes": self.num_classes
                }
            )
        
        # Training history
        history = {
            "train_loss": [],
            "train_accuracy": [],
            "val_loss": [],
            "val_accuracy": []
        }
        
        best_val_accuracy = 0.0
        
        console.print(f"🚀 Starting orientation classifier training for {epochs} epochs...")
        
        for epoch in range(epochs):
            console.print(f"\n📊 Epoch {epoch + 1}/{epochs}")
            
            # Train
            train_metrics = self.train_epoch(train_loader)
            
            # Validate
            val_metrics = self.validate_epoch(val_loader)
            
            # Update learning rate
            self.scheduler.step()
            
            # Store metrics
            history["train_loss"].append(train_metrics["loss"])
            history["train_accuracy"].append(train_metrics["accuracy"])
            history["val_loss"].append(val_metrics["loss"])
            history["val_accuracy"].append(val_metrics["accuracy"])
            
            # Print metrics
            console.print(f"   Train Loss: {train_metrics['loss']:.4f}, Accuracy: {train_metrics['accuracy']:.2f}%")
            console.print(f"   Val Loss: {val_metrics['loss']:.4f}, Accuracy: {val_metrics['accuracy']:.2f}%")
            
            # Log to W&B
            if use_wandb:
                wandb.log({
                    "epoch": epoch + 1,
                    "train_loss": train_metrics["loss"],
                    "train_accuracy": train_metrics["accuracy"],
                    "val_loss": val_metrics["loss"],
                    "val_accuracy": val_metrics["accuracy"],
                    "learning_rate": self.optimizer.param_groups[0]['lr']
                })
            
            # Save best model
            if val_metrics["accuracy"] > best_val_accuracy:
                best_val_accuracy = val_metrics["accuracy"]
                best_model_path = save_dir / f"best_{experiment_name}.pth"
                torch.save({
                    'epoch': epoch + 1,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                    'val_accuracy': val_metrics["accuracy"],
                    'val_loss': val_metrics["loss"]
                }, best_model_path)
                console.print(f"💾 New best model saved: {best_model_path}")
        
        console.print(f"\n✅ Training completed!")
        console.print(f"   Best validation accuracy: {best_val_accuracy:.2f}%")
        
        return history
    
    def predict(self, image: Image.Image) -> Tuple[int, float, str]:
        """Predict orientation of a component crop.
        
        Args:
            image: PIL Image of the component crop
            
        Returns:
            Tuple of (predicted_class, confidence, orientation_label)
        """
        self.model.eval()
        
        # Preprocess image
        input_tensor = self.val_transform(image).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(input_tensor)
            probabilities = F.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probabilities, 1)
            
            predicted_class = predicted.item()
            confidence_score = confidence.item()
            
            # Map to orientation label
            orientation_labels = {0: "0°", 1: "90°", 2: "180°", 3: "270°"}
            orientation_label = orientation_labels.get(predicted_class, "Unknown")
            
            return predicted_class, confidence_score, orientation_label
    
    def load_checkpoint(self, checkpoint_path: Path) -> bool:
        """Load model from checkpoint.
        
        Args:
            checkpoint_path: Path to the checkpoint file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            checkpoint = torch.load(checkpoint_path, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            
            console.print(f"✅ Model loaded from {checkpoint_path}")
            if 'val_accuracy' in checkpoint:
                console.print(f"   Checkpoint accuracy: {checkpoint['val_accuracy']:.2f}%")
                
            return True
            
        except Exception as e:
            console.print(f"❌ Error loading checkpoint: {e}")
            return False
    
    def export_onnx(self, 
                   checkpoint_path: Path,
                   output_path: Path,
                   input_size: Tuple[int, int] = (224, 224)) -> bool:
        """Export model to ONNX format.
        
        Args:
            checkpoint_path: Path to trained model checkpoint
            output_path: Output path for ONNX model
            input_size: Input image size (height, width)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load checkpoint
            if not self.load_checkpoint(checkpoint_path):
                return False
            
            self.model.eval()
            
            # Create dummy input
            dummy_input = torch.randn(1, 3, *input_size).to(self.device)
            
            # Export to ONNX
            output_path.parent.mkdir(parents=True, exist_ok=True)
            torch.onnx.export(
                self.model,
                dummy_input,
                str(output_path),
                export_params=True,
                opset_version=11,
                do_constant_folding=True,
                input_names=['input'],
                output_names=['output'],
                dynamic_axes={
                    'input': {0: 'batch_size'},
                    'output': {0: 'batch_size'}
                }
            )
            
            console.print(f"✅ ONNX model exported: {output_path}")
            
            # Verify export
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
            outputs = ort_session.run(None, {"input": dummy_input})
            
            console.print(f"✅ ONNX model verified successfully")
            console.print(f"   Input shape: {dummy_input.shape}")
            console.print(f"   Output shape: {outputs[0].shape}")
            
        except ImportError:
            console.print("⚠️  ONNX verification skipped (onnx/onnxruntime not installed)")
        except Exception as e:
            console.print(f"⚠️  ONNX verification failed: {e}")
    
    def evaluate_model(self, test_loader: DataLoader) -> Dict[str, Any]:
        """Evaluate model on test set with detailed metrics.
        
        Args:
            test_loader: Test data loader
            
        Returns:
            Detailed evaluation metrics
        """
        self.model.eval()
        
        all_predictions = []
        all_labels = []
        
        with torch.no_grad():
            for images, labels in track(test_loader, description="Evaluating..."):
                images = images.to(self.device)
                labels = labels.to(self.device)
                
                outputs = self.model(images)
                _, predicted = torch.max(outputs, 1)
                
                all_predictions.extend(predicted.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
        
        # Calculate metrics
        from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
        
        accuracy = accuracy_score(all_labels, all_predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            all_labels, all_predictions, average='weighted'
        )
        
        # Per-class metrics
        precision_per_class, recall_per_class, f1_per_class, _ = precision_recall_fscore_support(
            all_labels, all_predictions, average=None
        )
        
        # Confusion matrix
        cm = confusion_matrix(all_labels, all_predictions)
        
        results = {
            "accuracy": accuracy * 100,
            "precision": precision * 100,
            "recall": recall * 100,
            "f1_score": f1 * 100,
            "per_class_metrics": {
                f"{i}°": {
                    "precision": precision_per_class[i] * 100,
                    "recall": recall_per_class[i] * 100,
                    "f1_score": f1_per_class[i] * 100
                }
                for i in range(self.num_classes)
            },
            "confusion_matrix": cm.tolist()
        }
        
        console.print(f"\n📊 Evaluation Results:")
        console.print(f"   Overall Accuracy: {accuracy*100:.2f}%")
        console.print(f"   Precision: {precision*100:.2f}%")
        console.print(f"   Recall: {recall*100:.2f}%")
        console.print(f"   F1-Score: {f1*100:.2f}%")
        
        return results 