# Phase 2: Detection & OCR Models - Implementation Guide

*CircuitCLI Phase 2 Complete Implementation - Ready for Training*

---

## 🎯 **Phase 2 Overview**

**Goal**: Produce fast, accurate detectors that tag every symbol, text, junction, etc.

**Key Deliverables**:
- ✅ YOLOv8-seg detector for 60 electrical component classes
- ✅ Experiment tracking with TensorBoard/W&B
- ✅ ONNX model export and optimization
- ✅ Orientation classifier for rotated components  
- ✅ OCR integration for component value extraction
- ✅ Complete CLI interface for training and inference

**Target Metrics**:
- mAP ≥ 0.60 on validation set
- Rotation accuracy ≥ 95%
- OCR accuracy ≥ 90%
- Inference time ≤ 8s on laptop CPU

---

## 🏗️ **Implementation Architecture**

### **Core Components Created**

1. **`CircuitDetector`** (`src/circuitcli/models/detector.py`)
   - YOLOv8 wrapper with circuit-specific optimizations
   - Built-in experiment tracking (W&B + TensorBoard)
   - Automatic data configuration generation
   - Performance benchmarking tools

2. **`OrientationClassifier`** (`src/circuitcli/models/orientation_classifier.py`)
   - EfficientNet-B0 based lightweight classifier
   - 4-class orientation detection (0°, 90°, 180°, 270°)
   - Complete training pipeline with validation

3. **`CircuitOCR`** (`src/circuitcli/models/ocr_engine.py`)
   - EasyOCR integration with circuit-specific preprocessing
   - Regex-based component value extraction
   - Support for resistors, capacitors, inductors, voltage/current sources
   - Batch processing capabilities

4. **`ModelExporter`** (`src/circuitcli/models/model_export.py`)
   - ONNX export with optimization and quantization
   - Performance benchmarking and validation
   - Complete deployment package generation

### **CLI Commands Added**

```bash
# Train YOLOv8 detector
circuitcli models train-detector --epochs 100 --use-wandb --export-onnx

# Run inference
circuitcli models predict --image-path circuit.jpg --model-path best.pt

# Export to ONNX
circuitcli models export-onnx --checkpoint-path best.pt --output-path model.onnx

# Benchmark performance
circuitcli models benchmark --onnx-path model.onnx --num-runs 100
```

---

## 🚀 **Quick Start Training**

### **1. Environment Setup**

```bash
# Install additional ML dependencies
poetry install

# Or manually install key packages
pip install wandb tensorboardx easyocr onnx onnxruntime scikit-learn
```

### **2. Validate Implementation**

```bash
# Run comprehensive tests
python scripts/test_phase2_implementation.py
```

Expected output:
```
✅ PASS Detector Initialization
✅ PASS Orientation Classifier  
✅ PASS OCR Engine
✅ PASS Model Export
✅ PASS Dataset Availability
✅ PASS Quick Training Setup

🎯 Overall: 6/6 tests passed
🎉 All tests passed! Phase 2 implementation is ready.
```

### **3. Start YOLOv8 Training**

```bash
# Basic training (CPU/small dataset)
python scripts/train_detector.py \
    --model-size n \
    --epochs 50 \
    --batch-size 8 \
    --experiment-name circuit_detector_v1

# Production training (GPU + W&B)
python scripts/train_detector.py \
    --model-size m \
    --epochs 100 \
    --batch-size 16 \
    --use-wandb \
    --export-onnx \
    --experiment-name circuit_detector_production
```

### **4. Monitor Training**

- **TensorBoard**: `tensorboard --logdir runs/`
- **W&B Dashboard**: https://wandb.ai/ (if --use-wandb enabled)

---

## 📊 **Expected Training Results**

### **Dataset Statistics** (From Phase 1)
- **Training**: 1,696 images, 137,601 annotations
- **Validation**: 484 images, 39,976 annotations  
- **Test**: 244 images, 18,470 annotations
- **Classes**: 60 electrical components
- **Average annotations/image**: 80.9

### **Training Timeline** (YOLOv8n, 100 epochs)
- **GPU (RTX 4090)**: ~2-3 hours
- **GPU (GTX 1080)**: ~4-6 hours  
- **CPU**: ~20-30 hours (not recommended)

### **Expected Performance Metrics**

| Model Size | mAP@50 | mAP@50-95 | Inference (ms) | Model Size (MB) |
|------------|--------|-----------|----------------|-----------------|
| YOLOv8n    | 0.62   | 0.41      | 15-25          | 6.2            |
| YOLOv8s    | 0.68   | 0.46      | 20-35          | 21.5           |
| YOLOv8m    | 0.72   | 0.50      | 40-60          | 49.7           |

*Note: Actual results depend on dataset quality and training parameters*

---

## 🔧 **Advanced Training Configuration**

### **Custom Training Script**

```python
from circuitcli.models.detector import CircuitDetector

# Initialize detector  
detector = CircuitDetector(model_size="m", pretrained=True)

# Advanced training config
training_config = detector.setup_training_config(
    epochs=150,
    batch_size=32,  
    img_size=640,
    learning_rate=0.001,  # Lower LR for fine-tuning
    patience=30,
    save_period=5,
    use_wandb=True
)

# Train with custom augmentations
results = detector.train()

# Export optimized model
detector.export_onnx(
    checkpoint_path="best.pt",
    output_path="circuit_detector_optimized.onnx",
    optimize=True,
    simplify=True
)
```

### **Multi-GPU Training**

```bash
# Distributed training (4 GPUs)
python -m torch.distributed.launch \
    --nproc_per_node=4 \
    scripts/train_detector.py \
    --model-size l \
    --batch-size 64 \
    --epochs 200
```

---

## 🧭 **Orientation Classifier Training**

### **Data Preparation**

```python
from circuitcli.models.orientation_classifier import OrientationClassifier

# Create orientation dataset from detected components
# (This requires component crops from trained detector)

classifier = OrientationClassifier()
classifier.setup_training(learning_rate=0.001)

# Create data loaders
train_loader, val_loader = classifier.create_dataloaders(
    train_crops_dir="data/crops/train",
    val_crops_dir="data/crops/val", 
    train_annotations="data/crops/train_orientations.json",
    val_annotations="data/crops/val_orientations.json"
)

# Train classifier
history = classifier.train(
    train_loader, val_loader, 
    epochs=50,
    experiment_name="orientation_v1"
)
```

---

## 🔤 **OCR Integration Example**

### **Component Value Extraction**

```python
from circuitcli.models.ocr_engine import CircuitOCR
from PIL import Image

# Initialize OCR
ocr = CircuitOCR(languages=['en'], gpu=True)

# Process circuit image
image = Image.open("circuit.jpg")
results = ocr.process_circuit_image(image)

# Extract component values
for value in results['component_values']:
    print(f"Found {value['value_type']}: {value['parsed_value']['formatted']}")

# Extract component labels  
for label in results['component_labels']:
    print(f"Found {label['component_type']}: {label['designator']}")
```

---

## 📦 **Model Deployment**

### **ONNX Export Pipeline**

```python
from circuitcli.models.model_export import ModelExporter

exporter = ModelExporter()

# Export complete pipeline
exported_models = exporter.export_complete_pipeline(
    yolo_checkpoint="best_detector.pt",
    orientation_checkpoint="best_orientation.pth", 
    output_dir="deployment/",
    optimize=True,
    quantize=True
)

# Validate exported models
validation_results = exporter.validate_exported_models(
    exported_models,
    test_images=["test1.jpg", "test2.jpg"]
)
```

### **Performance Optimization**

```bash
# Export optimized models
circuitcli models export-onnx \
    --checkpoint-path best.pt \
    --output-path models/detector.onnx \
    --optimize \
    --quantize

# Benchmark performance
circuitcli models benchmark \
    --onnx-path models/detector.onnx \
    --num-runs 1000
```

---

## 🎯 **Success Criteria Validation**

### **Automated Evaluation**

```python
# Model performance validation
def validate_phase2_success():
    results = {}
    
    # 1. mAP ≥ 0.60 validation
    detector_metrics = validate_yolo_model("best.pt", "data/processed/splits/test.json")
    results['map50'] = detector_metrics['map50']
    results['map50_pass'] = detector_metrics['map50'] >= 0.60
    
    # 2. Orientation accuracy ≥ 95%
    orientation_metrics = validate_orientation_model("best_orientation.pth")
    results['orientation_accuracy'] = orientation_metrics['accuracy'] 
    results['orientation_pass'] = orientation_metrics['accuracy'] >= 95.0
    
    # 3. OCR accuracy ≥ 90%
    ocr_metrics = validate_ocr_accuracy("ground_truth.json")
    results['ocr_accuracy'] = ocr_metrics['overall_accuracy']
    results['ocr_pass'] = ocr_metrics['overall_accuracy'] >= 90.0
    
    # 4. Inference time ≤ 8s
    inference_metrics = benchmark_inference_time("detector.onnx")
    results['inference_time'] = inference_metrics['avg_inference_time_ms']
    results['speed_pass'] = inference_metrics['avg_inference_time_ms'] <= 8000
    
    return results
```

---

## 🐛 **Troubleshooting**

### **Common Issues**

1. **CUDA Out of Memory**
   ```bash
   # Reduce batch size and image size
   --batch-size 8 --img-size 320
   ```

2. **W&B Authentication**
   ```bash
   wandb login
   # Enter your API key from https://wandb.ai/settings
   ```

3. **EasyOCR Model Download**
   ```python
   # First run downloads models (~100MB)
   # Ensure internet connection and sufficient disk space
   ```

4. **ONNX Export Issues**
   ```bash
   # Install latest ONNX packages
   pip install onnx onnxruntime onnxoptimizer --upgrade
   ```

### **Performance Tuning**

- **Low mAP**: Increase epochs, try larger model size, check data quality
- **Slow Training**: Reduce batch size, use mixed precision (amp=True)
- **Overfitting**: Increase data augmentation, add dropout, early stopping

---

## 📈 **Next Steps After Phase 2**

1. **Model Optimization**
   - Hyperparameter tuning with Optuna
   - Knowledge distillation for faster inference
   - Multi-scale training and testing

2. **Data Enhancement** 
   - Active learning for difficult cases
   - Synthetic data generation improvements
   - Cross-domain validation

3. **Production Integration**
   - Docker containerization
   - REST API development
   - Edge deployment optimization

---

## 📋 **Phase 2 Checklist**

- [x] **YOLOv8 Detector Implementation**
  - [x] CircuitDetector class with training pipeline
  - [x] Data configuration generation
  - [x] Experiment tracking integration
  - [x] ONNX export functionality

- [x] **Orientation Classifier**
  - [x] EfficientNet-based architecture
  - [x] 4-class orientation detection
  - [x] Training and validation pipeline

- [x] **OCR Engine**
  - [x] EasyOCR integration
  - [x] Circuit-specific preprocessing
  - [x] Component value extraction
  - [x] Batch processing support

- [x] **Model Export & Optimization**
  - [x] ONNX export with verification
  - [x] Model optimization and quantization
  - [x] Performance benchmarking

- [x] **CLI Integration**
  - [x] Training commands
  - [x] Inference commands  
  - [x] Export and benchmark commands

- [x] **Testing & Validation**
  - [x] Comprehensive test suite
  - [x] Implementation validation
  - [x] Performance benchmarking

---

**Status**: ✅ **PHASE 2 COMPLETE - READY FOR TRAINING**

**Next Command**: 
```bash
python scripts/train_detector.py --epochs 100 --use-wandb --export-onnx
```

*Implementation by: Senior ML Engineer | CircuitCLI v0.1.0* 