"""Tests for dataset preparation functionality."""

import pytest
import tempfile
import json
from pathlib import Path
import numpy as np
from PIL import Image

# Add src to path for testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from circuitcli.dataset.constants import ALL_COMPONENT_CLASSES, DATASET_CONFIG
from circuitcli.dataset.augmentation_loader import AugmentationLoader
from circuitcli.dataset.synthetic_generator import SyntheticSchematicGenerator
from circuitcli.dataset.coco_validator import COCOValidator


class TestConstants:
    """Test dataset constants."""
    
    def test_component_classes_defined(self):
        """Test that component classes are properly defined."""
        assert len(ALL_COMPONENT_CLASSES) > 0
        assert "resistor" in ALL_COMPONENT_CLASSES
        assert "capacitor" in ALL_COMPONENT_CLASSES
        assert "junction" in ALL_COMPONENT_CLASSES
    
    def test_dataset_config(self):
        """Test dataset configuration."""
        assert DATASET_CONFIG["train_split"] + DATASET_CONFIG["val_split"] + DATASET_CONFIG["test_split"] == 1.0
        assert DATASET_CONFIG["random_seed"] == 42
        assert DATASET_CONFIG["min_bbox_area"] > 0


class TestAugmentationLoader:
    """Test augmentation configuration loading."""
    
    def test_load_valid_config(self):
        """Test loading a valid augmentation configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config = """
augmentations:
  - name: "HorizontalFlip"
    params:
      p: 0.5
  - name: "Rotate"
    params:
      limit: 15
      p: 0.3

validation_augmentations:
  - name: "Normalize"
    params:
      mean: [0.485, 0.456, 0.406]
      std: [0.229, 0.224, 0.225]
      max_pixel_value: 255.0

settings:
  bbox_format: "coco"
  min_visibility: 0.3
  min_area: 100
"""
            f.write(config)
            config_path = Path(f.name)
        
        try:
            loader = AugmentationLoader(config_path)
            assert loader.config is not None
            assert "train" in loader.pipelines
            assert "val" in loader.pipelines
        finally:
            config_path.unlink()
    
    def test_validate_config(self):
        """Test configuration validation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config = """
augmentations:
  - name: "HorizontalFlip"
    params:
      p: 0.5

settings:
  bbox_format: "coco"
"""
            f.write(config)
            config_path = Path(f.name)
        
        try:
            loader = AugmentationLoader(config_path)
            assert loader.validate_config() == True
        finally:
            config_path.unlink()


class TestSyntheticGenerator:
    """Test synthetic schematic generation."""
    
    def test_generator_initialization(self):
        """Test that generator initializes correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "synthetic"
            generator = SyntheticSchematicGenerator(output_dir)
            assert generator.output_dir == output_dir
            assert generator.canvas_size == (800, 600)
    
    def test_generate_single_schematic(self):
        """Test generation of a single schematic."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "synthetic"
            generator = SyntheticSchematicGenerator(output_dir)
            
            image_path, annotations = generator.generate_single_schematic(0, num_components=3)
            
            assert image_path.exists()
            assert len(annotations) <= 3  # May be fewer due to placement constraints
            assert image_path.suffix == ".png"
            
            # Verify image can be opened
            with Image.open(image_path) as img:
                assert img.size == generator.canvas_size


class TestCOCOValidator:
    """Test COCO dataset validation."""
    
    def create_minimal_coco_data(self):
        """Create minimal valid COCO data for testing."""
        return {
            "info": {
                "description": "Test dataset",
                "version": "1.0",
                "year": 2024,
                "contributor": "Test",
                "date_created": "2024-01-01"
            },
            "licenses": [{"id": 1, "name": "Test License", "url": ""}],
            "categories": [
                {"id": 1, "name": "resistor", "supercategory": "electrical_component"}
            ],
            "images": [
                {
                    "id": 1,
                    "width": 100,
                    "height": 100,
                    "file_name": "test.jpg"
                }
            ],
            "annotations": [
                {
                    "id": 1,
                    "image_id": 1,
                    "category_id": 1,
                    "bbox": [10, 10, 20, 20],
                    "area": 400,
                    "iscrowd": 0
                }
            ]
        }
    
    def test_load_coco_data(self):
        """Test loading COCO data."""
        coco_data = self.create_minimal_coco_data()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(coco_data, f)
            coco_path = Path(f.name)
        
        try:
            validator = COCOValidator(coco_path)
            assert validator.load_coco_data() == True
            assert validator.coco_data is not None
        finally:
            coco_path.unlink()
    
    def test_validate_structure(self):
        """Test COCO structure validation."""
        coco_data = self.create_minimal_coco_data()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(coco_data, f)
            coco_path = Path(f.name)
        
        try:
            validator = COCOValidator(coco_path)
            validator.load_coco_data()
            assert validator.validate_structure() == True
        finally:
            coco_path.unlink()
    
    def test_validate_consistency(self):
        """Test data consistency validation."""
        coco_data = self.create_minimal_coco_data()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(coco_data, f)
            coco_path = Path(f.name)
        
        try:
            validator = COCOValidator(coco_path)
            validator.load_coco_data()
            assert validator.validate_consistency() == True
        finally:
            coco_path.unlink()
    
    def test_generate_statistics(self):
        """Test statistics generation."""
        coco_data = self.create_minimal_coco_data()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(coco_data, f)
            coco_path = Path(f.name)
        
        try:
            validator = COCOValidator(coco_path)
            validator.load_coco_data()
            stats = validator.generate_statistics()
            
            assert stats["total_images"] == 1
            assert stats["total_annotations"] == 1
            assert stats["total_categories"] == 1
            assert "category_distribution" in stats
        finally:
            coco_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__]) 