"""CircuitCLI main command-line interface."""

import click
from pathlib import Path
from rich.console import Console

from .dataset.dvc_manager import DVCManager
from .dataset.pascal_to_coco import PascalToCOCOConverter, create_train_val_test_splits
from .dataset.synthetic_generator import SyntheticSchematicGenerator
from .dataset.augmentation_loader import AugmentationLoader
from .dataset.coco_validator import COCOValidator
from .dataset.cghd_adapter import CGHDDatasetAdapter

console = Console()


@click.group()
@click.version_option()
def main():
    """CircuitCLI - Image-to-Simulation Tool for Electrical Circuits."""
    pass


@main.group()
def dataset():
    """Dataset management and preparation commands."""
    pass


@main.group()
def models():
    """Model training and inference commands."""
    pass


@main.group()
def extract():
    """Extract circuit graph from detections."""
    pass


@dataset.command()
@click.option("--data-dir", type=click.Path(exists=True, path_type=Path), 
              default=Path("data"), help="Data directory path")
@click.option("--remote-url", type=str, 
              help="DVC remote URL (e.g., s3://bucket/path)")
@click.option("--remote-name", type=str, default="origin", 
              help="DVC remote name")
def init_dvc(data_dir: Path, remote_url: str, remote_name: str):
    """Initialize DVC for dataset versioning."""
    console.print("🚀 Initializing DVC for dataset management...")
    
    dvc_manager = DVCManager()
    
    # Initialize DVC
    if not dvc_manager.initialize_dvc():
        console.print("❌ Failed to initialize DVC")
        return
    
    # Add data directory to DVC tracking
    if data_dir.exists():
        if not dvc_manager.add_data_directory(data_dir):
            console.print("❌ Failed to add data directory to DVC")
            return
    
    # Set up remote if provided
    if remote_url:
        if not dvc_manager.setup_remote(remote_name, remote_url):
            console.print("❌ Failed to setup DVC remote")
            return
    
    console.print("✅ DVC initialization completed successfully!")


@dataset.command()
@click.option("--cghd-path", type=click.Path(exists=True, path_type=Path),
              default=Path("data/cghd-zenodo-12"),
              help="Path to CGHD dataset root directory")
@click.option("--train-ratio", type=float, default=0.7,
              help="Training set ratio")
@click.option("--val-ratio", type=float, default=0.2,
              help="Validation set ratio")
@click.option("--test-ratio", type=float, default=0.1,
              help="Test set ratio")
@click.option("--seed", type=int, default=42,
              help="Random seed for reproducible splits")
def process_cghd(cghd_path: Path, train_ratio: float, val_ratio: float, 
                test_ratio: float, seed: int):
    """Process CGHD dataset for CircuitCLI pipeline."""
    console.print("🚀 Processing CGHD dataset...")
    
    # Validate ratios
    if abs(train_ratio + val_ratio + test_ratio - 1.0) > 0.01:
        console.print("❌ Split ratios must sum to 1.0")
        return
    
    try:
        adapter = CGHDDatasetAdapter(cghd_path)
        
        if adapter.process_full_dataset(train_ratio, val_ratio, test_ratio, seed):
            console.print("✅ CGHD dataset processing completed successfully!")
        else:
            console.print("❌ CGHD dataset processing failed")
            
    except Exception as e:
        console.print(f"❌ Error processing CGHD dataset: {e}")


@dataset.command()
@click.option("--images-dir", type=click.Path(exists=True, path_type=Path), 
              required=True, help="Directory containing images")
@click.option("--annotations-dir", type=click.Path(exists=True, path_type=Path), 
              required=True, help="Directory containing Pascal VOC XML files")
@click.option("--output-path", type=click.Path(path_type=Path), 
              default=Path("data/annotations/dataset.json"),
              help="Output path for COCO JSON file")
def convert_pascal_to_coco(images_dir: Path, annotations_dir: Path, output_path: Path):
    """Convert Pascal VOC annotations to COCO JSON format."""
    console.print("🔄 Converting Pascal VOC to COCO format...")
    
    converter = PascalToCOCOConverter(images_dir, annotations_dir)
    
    if converter.convert_dataset(output_path):
        console.print("✅ Conversion completed successfully!")
    else:
        console.print("❌ Conversion failed")


@dataset.command()
@click.option("--coco-json", type=click.Path(exists=True, path_type=Path), 
              required=True, help="Path to COCO JSON file")
@click.option("--output-dir", type=click.Path(path_type=Path), 
              default=Path("data/splits"),
              help="Output directory for split files")
@click.option("--train-ratio", type=float, default=0.7, 
              help="Training set ratio")
@click.option("--val-ratio", type=float, default=0.2, 
              help="Validation set ratio")
@click.option("--test-ratio", type=float, default=0.1, 
              help="Test set ratio")
@click.option("--seed", type=int, default=42, 
              help="Random seed for reproducible splits")
def create_splits(coco_json: Path, output_dir: Path, train_ratio: float, 
                 val_ratio: float, test_ratio: float, seed: int):
    """Create train/validation/test splits from COCO dataset."""
    console.print("📊 Creating dataset splits...")
    
    # Validate ratios
    if abs(train_ratio + val_ratio + test_ratio - 1.0) > 0.01:
        console.print("❌ Split ratios must sum to 1.0")
        return
    
    if create_train_val_test_splits(
        coco_json, output_dir, train_ratio, val_ratio, test_ratio, seed
    ):
        console.print("✅ Dataset splits created successfully!")
    else:
        console.print("❌ Split creation failed")


@dataset.command()
@click.option("--output-dir", type=click.Path(path_type=Path), 
              default=Path("data/synthetic"),
              help="Output directory for synthetic images")
@click.option("--num-images", type=int, default=100, 
              help="Number of synthetic images to generate")
@click.option("--canvas-size", type=str, default="800x600", 
              help="Canvas size as WIDTHxHEIGHT")
def generate_synthetic(output_dir: Path, num_images: int, canvas_size: str):
    """Generate synthetic printed schematic images."""
    console.print("🎨 Generating synthetic schematic images...")
    
    # Parse canvas size
    try:
        width, height = map(int, canvas_size.split('x'))
        canvas_size_tuple = (width, height)
    except ValueError:
        console.print("❌ Invalid canvas size format. Use WIDTHxHEIGHT (e.g., 800x600)")
        return
    
    generator = SyntheticSchematicGenerator(output_dir, canvas_size_tuple)
    
    if generator.generate_dataset(num_images):
        console.print("✅ Synthetic dataset generation completed!")
    else:
        console.print("❌ Synthetic generation failed")


@dataset.command()
@click.option("--config-path", type=click.Path(exists=True, path_type=Path), 
              default=Path("config/augmentations.yaml"),
              help="Path to augmentation configuration YAML")
def validate_augmentations(config_path: Path):
    """Validate augmentation configuration."""
    console.print("🔍 Validating augmentation configuration...")
    
    try:
        loader = AugmentationLoader(config_path)
        
        if loader.validate_config():
            console.print("✅ Augmentation configuration is valid!")
            
            # Print summary
            summary = loader.get_config_summary()
            console.print(f"📋 Configuration Summary:")
            console.print(f"   Config file: {summary['config_path']}")
            console.print(f"   Pipelines: {', '.join(summary['pipelines'])}")
            for pipeline in summary['pipelines']:
                count_key = f"{pipeline}_transforms_count"
                if count_key in summary:
                    console.print(f"   {pipeline.capitalize()} transforms: {summary[count_key]}")
        else:
            console.print("❌ Augmentation configuration validation failed")
            
    except Exception as e:
        console.print(f"❌ Error validating augmentation config: {e}")


@dataset.command()
@click.option("--coco-json", type=click.Path(exists=True, path_type=Path), 
              required=True, help="Path to COCO JSON file")
@click.option("--images-dir", type=click.Path(exists=True, path_type=Path), 
              help="Directory containing images (for file validation)")
def validate_coco(coco_json: Path, images_dir: Path):
    """Validate COCO dataset format and content."""
    console.print("🔍 Validating COCO dataset...")
    
    validator = COCOValidator(coco_json, images_dir)
    
    if validator.validate_all():
        console.print("✅ COCO dataset validation passed!")
    else:
        console.print("❌ COCO dataset validation failed")


@dataset.command()
@click.option("--use-cghd", is_flag=True, default=True,
              help="Use CGHD dataset for setup")
@click.option("--cghd-path", type=click.Path(exists=True, path_type=Path),
              default=Path("data/cghd-zenodo-12"),
              help="Path to CGHD dataset")
def setup(use_cghd: bool, cghd_path: Path):
    """Complete dataset setup workflow."""
    console.print("🚀 Starting CircuitCLI dataset setup workflow...")
    
    if use_cghd and cghd_path.exists():
        console.print("🎯 Using CGHD dataset for setup")
        
        # Step 1: Initialize DVC (local only)
        console.print("\n📦 Step 1: Initializing DVC (local)...")
        dvc_manager = DVCManager()
        dvc_manager.initialize_dvc()
        
        # Step 2: Process CGHD dataset
        console.print("\n🔄 Step 2: Processing CGHD dataset...")
        try:
            adapter = CGHDDatasetAdapter(cghd_path)
            if adapter.process_full_dataset():
                console.print("✅ CGHD processing completed")
            else:
                console.print("❌ CGHD processing failed")
                return
        except Exception as e:
            console.print(f"❌ Error processing CGHD: {e}")
            return
        
        # Step 3: Validate processed datasets
        console.print("\n🔍 Step 3: Validating processed datasets...")
        processed_splits = Path("data/processed/splits")
        processed_images = Path("data/processed/organized/images")
        
        for split in ["train", "val", "test"]:
            split_file = processed_splits / f"{split}.json"
            if split_file.exists():
                console.print(f"Validating {split} split...")
                validator = COCOValidator(split_file, processed_images)
                validator.validate_all()
        
        # Step 4: Validate augmentation config
        console.print("\n🔍 Step 4: Validating augmentation configuration...")
        aug_config = Path("config/augmentations.yaml")
        if aug_config.exists():
            loader = AugmentationLoader(aug_config)
            loader.validate_config()
        
        # Step 5: Add to DVC tracking
        console.print("\n📦 Step 5: Adding processed data to DVC...")
        processed_dir = Path("data/processed")
        if processed_dir.exists():
            dvc_manager.add_data_directory(processed_dir)
        
        console.print("\n🎉 CGHD dataset setup completed successfully!")
        console.print("📄 Ready for training with:")
        console.print("   - data/processed/splits/train.json")
        console.print("   - data/processed/splits/val.json") 
        console.print("   - data/processed/splits/test.json")
        console.print("   - data/processed/organized/images/")
        
    else:
        console.print("❌ CGHD dataset not found or not requested")
        console.print(f"Please ensure CGHD dataset exists at: {cghd_path}")
        console.print("Or run the generic setup with your own data")
    
    console.print("\n🚀 Ready for Phase 2: Detection & OCR Models!")


@models.command()
@click.option("--data-dir", type=click.Path(exists=True, path_type=Path), 
              default=Path("data/processed"), help="Directory containing processed dataset")
@click.option("--model-size", type=click.Choice(["n", "s", "m", "l", "x"]), 
              default="n", help="YOLOv8 model size")
@click.option("--epochs", type=int, default=100, help="Number of training epochs")
@click.option("--batch-size", type=int, default=16, help="Training batch size")
@click.option("--img-size", type=int, default=640, help="Input image size")
@click.option("--learning-rate", type=float, default=0.01, help="Initial learning rate")
@click.option("--patience", type=int, default=50, help="Early stopping patience")
@click.option("--experiment-name", type=str, default="circuit_detection_v1", 
              help="Experiment name")
@click.option("--use-wandb", is_flag=True, help="Use Weights & Biases for experiment tracking")
@click.option("--resume", type=click.Path(path_type=Path), 
              help="Resume training from checkpoint")
@click.option("--export-onnx", is_flag=True, 
              help="Export best model to ONNX after training")
@click.option("--device", type=str, help="Device to use (cpu, cuda, mps)")
def train_detector(data_dir: Path, model_size: str, epochs: int, batch_size: int,
                  img_size: int, learning_rate: float, patience: int, 
                  experiment_name: str, use_wandb: bool, resume: Path,
                  export_onnx: bool, device: str):
    """Train YOLOv8 electrical component detector."""
    from .models.detector import CircuitDetector
    from .models.model_export import ModelExporter
    
    console.print("🚀 Starting YOLOv8 detector training...")
    
    # Setup paths
    splits_dir = data_dir / "splits"
    images_dir = data_dir / "organized" / "images"
    
    if not splits_dir.exists():
        console.print(f"❌ Splits directory not found: {splits_dir}")
        return
    
    if not images_dir.exists():
        console.print(f"❌ Images directory not found: {images_dir}")
        return
    
    try:
        # Setup data configuration
        data_config_path = Path("config/yolo_data.yaml")
        detector = CircuitDetector(model_size=model_size, device=device)
        
        train_json = splits_dir / "train.json"
        val_json = splits_dir / "val.json"
        test_json = splits_dir / "test.json"
        
        detector.create_data_config(train_json, val_json, test_json, 
                                  images_dir, data_config_path)
        
        # Setup training
        detector.setup_training_config(
            data_config_path=data_config_path,
            experiment_name=experiment_name,
            epochs=epochs,
            batch_size=batch_size,
            img_size=img_size,
            learning_rate=learning_rate,
            patience=patience,
            use_wandb=use_wandb,
            use_tensorboard=True
        )
        
        # Train model
        results = detector.train(resume=resume is not None, resume_path=resume)
        
        # Export ONNX if requested
        if export_onnx:
            best_checkpoint = Path(f"circuitcli/{experiment_name}/weights/best.pt")
            if best_checkpoint.exists():
                onnx_output = Path(f"models/{experiment_name}_best.onnx")
                detector.export_onnx(best_checkpoint, onnx_output)
        
        console.print("✅ Training completed successfully!")
        
    except Exception as e:
        console.print(f"❌ Training failed: {e}")


@models.command()
@click.option("--image-path", type=click.Path(exists=True, path_type=Path),
              required=True, help="Path to input image")
@click.option("--model-path", type=click.Path(exists=True, path_type=Path),
              required=True, help="Path to trained model")
@click.option("--conf-threshold", type=float, default=0.25,
              help="Confidence threshold for detections")
@click.option("--iou-threshold", type=float, default=0.45,
              help="IoU threshold for NMS")
@click.option("--output-dir", type=click.Path(path_type=Path),
              default=Path("results"), help="Output directory for results")
@click.option("--save-visualization", is_flag=True,
              help="Save visualization of detections")
def predict(image_path: Path, model_path: Path, conf_threshold: float,
           iou_threshold: float, output_dir: Path, save_visualization: bool):
    """Run inference on circuit images."""
    from .models.detector import CircuitDetector
    
    console.print(f"🔍 Running inference on {image_path}")
    
    try:
        detector = CircuitDetector()
        results = detector.predict(
            image_path=image_path,
            checkpoint_path=model_path,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            save_results=save_visualization
        )
        
        if results:
            console.print(f"✅ Found {len(results.boxes)} detections")
            console.print(f"📁 Results saved to: {output_dir}")
        else:
            console.print("❌ No detections found")
            
    except Exception as e:
        console.print(f"❌ Prediction failed: {e}")


@models.command()
@click.option("--checkpoint-path", type=click.Path(exists=True, path_type=Path),
              required=True, help="Path to model checkpoint")
@click.option("--output-path", type=click.Path(path_type=Path),
              required=True, help="Output path for ONNX model")
@click.option("--input-size", type=str, default="640x640",
              help="Input image size as WIDTHxHEIGHT")
@click.option("--optimize", is_flag=True, help="Optimize ONNX model")
@click.option("--quantize", is_flag=True, help="Quantize ONNX model")
def export_onnx(checkpoint_path: Path, output_path: Path, input_size: str,
               optimize: bool, quantize: bool):
    """Export trained model to ONNX format."""
    from .models.model_export import ModelExporter
    
    console.print(f"📦 Exporting model to ONNX...")
    
    try:
        # Parse input size
        width, height = map(int, input_size.split('x'))
        input_shape = (height, width)
        
        exporter = ModelExporter()
        
        # Export to ONNX
        if exporter.export_yolo_to_onnx(checkpoint_path, output_path, input_shape):
            console.print(f"✅ Model exported: {output_path}")
            
            # Optimize if requested
            if optimize:
                optimized_path = output_path.with_stem(output_path.stem + "_optimized")
                if exporter.optimize_onnx_model(output_path, optimized_path):
                    console.print(f"⚡ Optimized model: {optimized_path}")
            
            # Quantize if requested
            if quantize:
                quantized_path = output_path.with_stem(output_path.stem + "_quantized")
                if exporter.quantize_onnx_model(output_path, quantized_path):
                    console.print(f"🔢 Quantized model: {quantized_path}")
        else:
            console.print("❌ Export failed")
            
    except Exception as e:
        console.print(f"❌ Export failed: {e}")


@models.command()
@click.option("--onnx-path", type=click.Path(exists=True, path_type=Path),
              required=True, help="Path to ONNX model")
@click.option("--input-size", type=str, default="640x640",
              help="Input image size as WIDTHxHEIGHT")
@click.option("--num-runs", type=int, default=100,
              help="Number of inference runs for benchmarking")
def benchmark(onnx_path: Path, input_size: str, num_runs: int):
    """Benchmark ONNX model performance."""
    from .models.model_export import ModelExporter
    
    console.print(f"🏁 Benchmarking model performance...")
    
    try:
        # Parse input size
        width, height = map(int, input_size.split('x'))
        input_shape = (1, 3, height, width)
        
        exporter = ModelExporter()
        metrics = exporter.benchmark_onnx_model(onnx_path, input_shape, num_runs)
        
        if metrics:
            console.print("✅ Benchmark completed!")
        else:
            console.print("❌ Benchmark failed")
            
    except Exception as e:
        console.print(f"❌ Benchmark failed: {e}")


@extract.command()
@click.argument("detections_json", type=click.Path(exists=True, path_type=Path))
@click.option("--image-path", type=click.Path(exists=True, path_type=Path), 
              required=True, help="Path to original circuit image")
@click.option("--graph", type=click.Path(path_type=Path), 
              required=True, help="Output path for circuit graph JSON")
@click.option("--orientations", type=click.Path(exists=True, path_type=Path),
              help="Path to orientations JSON file")
@click.option("--pin-templates", type=click.Path(exists=True, path_type=Path),
              default=Path("config/pin_templates.yaml"),
              help="Path to pin templates configuration")
@click.option("--visualize", type=click.Path(path_type=Path),
              help="Save graph visualization to this path")
@click.option("--debug-dir", type=click.Path(path_type=Path),
              help="Directory to save debug images")
def graph(detections_json: Path, image_path: Path, graph: Path, 
         orientations: Path, pin_templates: Path, visualize: Path, debug_dir: Path):
    """Extract circuit graph from detections JSON."""
    console.print("🔗 Extracting circuit graph from detections...")
    
    try:
        from .models import WireDetector, GraphVisualizer, load_detections_from_json, save_graph_to_json
        import json
        
        # Load detections
        detections = load_detections_from_json(detections_json)
        if not detections:
            console.print("❌ No detections found")
            return
        
        # Load orientations if provided
        orientation_data = {}
        if orientations and orientations.exists():
            with open(orientations, 'r') as f:
                orientation_data = json.load(f)
        
        # Create wire detector
        wire_detector = WireDetector(pin_templates)
        
        # Create circuit graph
        circuit_graph = wire_detector.create_circuit_graph(
            image_path, detections, orientation_data
        )
        
        # Save graph
        graph.parent.mkdir(exist_ok=True, parents=True)
        if save_graph_to_json(circuit_graph, graph):
            console.print(f"✅ Circuit graph saved to {graph}")
        
        # Save visualization if requested
        if visualize:
            visualizer = GraphVisualizer()
            visualize.parent.mkdir(exist_ok=True, parents=True)
            if visualizer.visualize_graph(circuit_graph, visualize):
                console.print(f"📊 Graph visualization saved to {visualize}")
        
        # Save debug images if requested
        if debug_dir:
            wire_detector.save_debug_images(debug_dir)
        
        # Print summary
        console.print(f"📈 Graph Summary:")
        console.print(f"   Total nodes: {len(circuit_graph.nodes)}")
        console.print(f"   Total edges: {len(circuit_graph.edges)}")
        
        # Count node types
        node_types = {}
        for _, data in circuit_graph.nodes(data=True):
            node_type = data.get('type', 'unknown')
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        for node_type, count in node_types.items():
            console.print(f"   {node_type} nodes: {count}")
        
    except Exception as e:
        console.print(f"❌ Error extracting circuit graph: {e}")
        raise


if __name__ == "__main__":
    main() 