"""Load and apply Albumentations augmentation pipelines from YAML configuration."""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import albumentations as A
import cv2
import numpy as np
from rich.console import Console

console = Console()


class AugmentationLoader:
    """Load and manage Albumentations pipelines from YAML configuration."""
    
    def __init__(self, config_path: Path):
        """Initialize the augmentation loader."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.pipelines = self._create_pipelines()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load the YAML configuration file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            console.print(f"✅ Loaded augmentation config from {self.config_path}")
            return config
        except Exception as e:
            console.print(f"❌ Error loading config {self.config_path}: {e}")
            raise
    
    def _create_transform_from_config(self, transform_config: Dict[str, Any]) -> A.BasicTransform:
        """Create a single Albumentations transform from configuration."""
        transform_name = transform_config["name"]
        params = transform_config.get("params", {})
        
        # Handle nested transforms for OneOf
        if transform_name == "OneOf":
            nested_transforms = []
            for nested_config in params.get("transforms", []):
                nested_transform = self._create_transform_from_config(nested_config)
                nested_transforms.append(nested_transform)
            params["transforms"] = nested_transforms
        
        try:
            transform_class = getattr(A, transform_name)
            return transform_class(**params)
        except AttributeError:
            console.print(f"❌ Unknown transform: {transform_name}")
            raise ValueError(f"Transform {transform_name} not found in Albumentations")
    
    def _create_pipelines(self) -> Dict[str, A.Compose]:
        """Create augmentation pipelines for different splits."""
        pipelines = {}
        
        # Training augmentations
        if "augmentations" in self.config:
            train_transforms = []
            for transform_config in self.config["augmentations"]:
                transform = self._create_transform_from_config(transform_config)
                train_transforms.append(transform)
            
            pipelines["train"] = A.Compose(
                train_transforms,
                bbox_params=A.BboxParams(
                    format=self.config.get("settings", {}).get("bbox_format", "coco"),
                    min_visibility=self.config.get("settings", {}).get("min_visibility", 0.3),
                    min_area=self.config.get("settings", {}).get("min_area", 100),
                    label_fields=["category_ids"]
                )
            )
        
        # Validation augmentations
        if "validation_augmentations" in self.config:
            val_transforms = []
            for transform_config in self.config["validation_augmentations"]:
                transform = self._create_transform_from_config(transform_config)
                val_transforms.append(transform)
            
            pipelines["val"] = A.Compose(val_transforms)
        
        # Test augmentations
        if "test_augmentations" in self.config:
            test_transforms = []
            for transform_config in self.config["test_augmentations"]:
                transform = self._create_transform_from_config(transform_config)
                test_transforms.append(transform)
            
            pipelines["test"] = A.Compose(test_transforms)
        
        console.print(f"✅ Created {len(pipelines)} augmentation pipelines")
        return pipelines
    
    def get_pipeline(self, split: str) -> Optional[A.Compose]:
        """Get augmentation pipeline for a specific split."""
        return self.pipelines.get(split)
    
    def apply_augmentations(self, 
                          image: np.ndarray, 
                          bboxes: List[List[float]], 
                          category_ids: List[int],
                          split: str = "train") -> Tuple[np.ndarray, List[List[float]], List[int]]:
        """Apply augmentations to an image and its bounding boxes."""
        pipeline = self.get_pipeline(split)
        
        if pipeline is None:
            console.print(f"⚠️  No pipeline found for split: {split}")
            return image, bboxes, category_ids
        
        try:
            if split == "train" and bboxes:
                # Apply with bounding boxes for training
                transformed = pipeline(
                    image=image,
                    bboxes=bboxes,
                    category_ids=category_ids
                )
                return (
                    transformed["image"],
                    transformed["bboxes"],
                    transformed["category_ids"]
                )
            else:
                # Apply without bounding boxes for val/test
                transformed = pipeline(image=image)
                return transformed["image"], bboxes, category_ids
            
        except Exception as e:
            console.print(f"❌ Error applying augmentations: {e}")
            return image, bboxes, category_ids
    
    def validate_config(self) -> bool:
        """Validate the augmentation configuration."""
        try:
            if not self.pipelines:
                console.print("❌ No valid augmentation pipelines found")
                return False
            
            # Test with dummy data
            dummy_image = np.ones((100, 100, 3), dtype=np.uint8) * 255
            dummy_bboxes = [[10, 10, 20, 20]]
            dummy_category_ids = [1]
            
            for split, pipeline in self.pipelines.items():
                try:
                    if split == "train":
                        result = pipeline(
                            image=dummy_image,
                            bboxes=dummy_bboxes,
                            category_ids=dummy_category_ids
                        )
                    else:
                        result = pipeline(image=dummy_image)
                    console.print(f"✅ Pipeline '{split}' validation passed")
                except Exception as e:
                    console.print(f"❌ Pipeline '{split}' validation failed: {e}")
                    return False
            
            console.print("✅ All augmentation pipelines validated successfully")
            return True
            
        except Exception as e:
            console.print(f"❌ Configuration validation error: {e}")
            return False 