# Dataset Audit & Preparation - Phase 1

This document provides a complete guide for setting up the CircuitCLI dataset preparation pipeline.

## Overview

The Dataset Audit & Preparation phase creates a reproducible, version-controlled dataset pipeline that:

1. **Manages raw data** with DVC version control
2. **Converts** Pascal VOC XML annotations to COCO JSON format
3. **Creates** train/validation/test splits
4. **Generates** synthetic printed schematics for domain diversity
5. **Configures** Albumentations augmentation pipelines
6. **Validates** dataset integrity and format compliance

## Quick Start

### 1. Install Dependencies

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install

# Or with pip
pip install -e .
```

### 2. Run Complete Setup

```bash
# Option 1: Using the CLI
poetry run circuitcli dataset setup

# Option 2: Using the standalone script
python scripts/setup_dataset.py

# Option 3: Manual step-by-step (see below)
```

## Directory Structure

The setup creates the following directory structure:

```
circuit2/
├── data/
│   ├── raw/
│   │   ├── images/          # Raw image files
│   │   └── annotations/     # Pascal VOC XML files
│   ├── annotations/
│   │   └── dataset.json     # Converted COCO format
│   ├── splits/
│   │   ├── train.json       # Training split
│   │   ├── val.json         # Validation split
│   │   └── test.json        # Test split
│   └── synthetic/           # Generated synthetic images
├── config/
│   └── augmentations.yaml   # Augmentation configuration
└── scripts/
    └── setup_dataset.py     # Standalone setup script
```

## Manual Step-by-Step Setup

### Step 1: Initialize DVC

```bash
# Initialize DVC repository
poetry run circuitcli dataset init-dvc --data-dir data

# With remote storage (optional)
poetry run circuitcli dataset init-dvc \
    --data-dir data \
    --remote-url s3://your-bucket/circuitcli-data \
    --remote-name origin
```

### Step 2: Prepare Raw Data

Place your data in the following structure:

```
data/raw/
├── images/
│   ├── image001.jpg
│   ├── image002.jpg
│   └── ...
└── annotations/
    ├── image001.xml
    ├── image002.xml
    └── ...
```

### Step 3: Convert Pascal VOC to COCO

```bash
poetry run circuitcli dataset convert-pascal-to-coco \
    --images-dir data/raw/images \
    --annotations-dir data/raw/annotations \
    --output-path data/annotations/dataset.json
```

### Step 4: Create Train/Val/Test Splits

```bash
poetry run circuitcli dataset create-splits \
    --coco-json data/annotations/dataset.json \
    --output-dir data/splits \
    --train-ratio 0.7 \
    --val-ratio 0.2 \
    --test-ratio 0.1
```

### Step 5: Generate Synthetic Data

```bash
poetry run circuitcli dataset generate-synthetic \
    --output-dir data/synthetic \
    --num-images 100 \
    --canvas-size 800x600
```

### Step 6: Validate Datasets

```bash
# Validate COCO format
poetry run circuitcli dataset validate-coco \
    --coco-json data/splits/train.json \
    --images-dir data/raw/images

# Validate augmentation config
poetry run circuitcli dataset validate-augmentations \
    --config-path config/augmentations.yaml
```

## Configuration

### Electrical Component Classes

The system recognizes 45+ electrical component classes including:

- **Passive Components**: resistor, capacitor, inductor, transformer
- **Active Components**: transistor, diode, opamp, LED
- **Logic Gates**: AND, OR, NOT, NAND, NOR, XOR
- **Sources**: voltage_source, current_source, battery
- **Connections**: wire, junction, crossover, terminal, ground

See `src/circuitcli/dataset/constants.py` for the complete list.

### Augmentation Configuration

The `config/augmentations.yaml` file defines:

- **Training augmentations**: Geometric transforms, photometric changes, noise, blur
- **Validation augmentations**: Minimal preprocessing (normalization only)
- **Test augmentations**: Same as validation

Key augmentation categories:
- Geometric: rotation, perspective, affine transforms
- Photometric: brightness, contrast, color shifts
- Quality: blur, noise, compression artifacts
- Realism: shadow effects, grid distortion

### Dataset Splits

Default configuration:
- **Training**: 70% of data
- **Validation**: 20% of data  
- **Test**: 10% of data
- **Random seed**: 42 (for reproducibility)

## Validation Criteria

The setup validates:

1. **COCO Format Compliance**
   - Required fields present
   - Unique IDs
   - Valid references between images/annotations/categories
   - Bounding box coordinates within image bounds

2. **Data Integrity**
   - Image files exist and match metadata
   - Annotation areas computed correctly
   - No corrupt or missing files

3. **Augmentation Pipeline**
   - Configuration loads without errors
   - Transforms apply successfully to test data
   - Bounding box handling works correctly

## Success Criteria (Phase 1)

✅ **All data behind `dvc pull`**: Raw and processed data managed by DVC
✅ **COCO JSON validation passes**: All splits conform to COCO format
✅ **Augmentation config loads**: Albumentations pipelines work correctly
✅ **Synthetic data generated**: Domain diversity enhanced with printed schematics

## Troubleshooting

### Common Issues

1. **DVC Installation Problems**
   ```bash
   # Install DVC with specific extras
   pip install 'dvc[s3]' 'dvc[gs]' 'dvc[azure]'
   ```

2. **Missing Dependencies**
   ```bash
   # Ensure all ML dependencies are installed
   pip install torch torchvision albumentations opencv-python
   ```

3. **COCO Validation Failures**
   - Check image file paths and dimensions
   - Verify annotation XML format
   - Ensure bounding boxes are within image bounds

4. **Augmentation Config Errors**
   - Validate YAML syntax
   - Check transform parameter names
   - Test with minimal configuration first

### Debugging Commands

```bash
# Test individual components
python -m pytest tests/test_dataset_preparation.py -v

# Validate specific COCO file
poetry run circuitcli dataset validate-coco \
    --coco-json data/splits/train.json \
    --images-dir data/raw/images

# Check augmentation config
poetry run circuitcli dataset validate-augmentations \
    --config-path config/augmentations.yaml
```

## Next Steps

After successful completion of Phase 1:

1. **Review generated files** in the `data/` directory
2. **Commit DVC files** to Git (not the actual data)
3. **Set up remote storage** for team collaboration
4. **Proceed to Phase 2**: Detection & OCR Models

## DVC Commands Reference

```bash
# Pull latest data
dvc pull

# Push data to remote
dvc push

# Check data status
dvc status

# Add new data
dvc add data/new_dataset

# Commit changes
git add data.dvc .gitignore
git commit -m "Add new dataset version"
```

## API Reference

### Command Line Interface

```bash
circuitcli dataset --help                    # Show all dataset commands
circuitcli dataset init-dvc --help          # DVC initialization options
circuitcli dataset convert-pascal-to-coco --help  # Conversion options
circuitcli dataset create-splits --help     # Split creation options
circuitcli dataset generate-synthetic --help # Synthetic generation options
circuitcli dataset validate-coco --help     # COCO validation options
circuitcli dataset validate-augmentations --help  # Augmentation validation
```

### Python API

```python
from circuitcli.dataset.dvc_manager import DVCManager
from circuitcli.dataset.pascal_to_coco import PascalToCOCOConverter
from circuitcli.dataset.synthetic_generator import SyntheticSchematicGenerator
from circuitcli.dataset.augmentation_loader import AugmentationLoader
from circuitcli.dataset.coco_validator import COCOValidator

# Example usage
converter = PascalToCOCOConverter(images_dir, annotations_dir)
converter.convert_dataset(output_path)

validator = COCOValidator(coco_json_path, images_dir)
validator.validate_all()
```

---

**Phase 1 Complete!** 🎉 Ready to move to Detection & OCR Models (Phase 2). 