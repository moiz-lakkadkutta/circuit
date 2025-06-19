#!/usr/bin/env python3
"""Quick test script for the trained model."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from circuitcli.models.detector import CircuitDetector

def quick_test():
    # Initialize detector
    detector = CircuitDetector()
    
    # Path to your trained model
    model_path = Path("circuitcli/circuit_detection_v1/weights/best.pt")
    
    if not model_path.exists():
        print(f"❌ Model not found at {model_path}")
        print("Make sure you've trained the model first!")
        return
    
    # Test image path (adjust this to your test image)
    test_image = Path("path/to/your/test_image.jpg")
    
    if not test_image.exists():
        print(f"❌ Test image not found at {test_image}")
        print("Please provide a valid test image path")
        return
    
    print(f"🔍 Testing model: {model_path}")
    print(f"📸 Test image: {test_image}")
    
    # Run prediction
    results = detector.predict(
        image_path=test_image,
        checkpoint_path=model_path,
        conf_threshold=0.25,
        iou_threshold=0.45,
        save_results=True
    )
    
    if results and results.boxes is not None:
        print(f"✅ Found {len(results.boxes)} detections!")
        print("📁 Visualization saved to: runs/predict/circuit_detection/")
        
        # Print detection details
        for i, box in enumerate(results.boxes):
            class_id = int(box.cls.item()) if box.cls is not None else -1
            confidence = float(box.conf.item()) if box.conf is not None else 0.0
            bbox = box.xyxy.cpu().numpy().tolist()[0] if box.xyxy is not None else []
            
            print(f"Detection {i+1}: Class={class_id}, Confidence={confidence:.3f}, BBox={bbox}")
    else:
        print("❌ No detections found")

if __name__ == "__main__":
    quick_test() 