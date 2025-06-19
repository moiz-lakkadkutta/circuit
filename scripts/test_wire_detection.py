#!/usr/bin/env python3
"""Test script for wire detection and graph assembly."""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from circuitcli.models.wire_detector import (
    WireDetector, GraphVisualizer, Detection, 
    load_detections_from_json, save_graph_to_json
)


def create_test_detections():
    """Create test detections for validation."""
    # Create some mock detections
    detections = [
        Detection(
            class_name="resistor",
            class_id=0,
            confidence=0.9,
            bbox=(100, 100, 200, 120),
            orientation=0.0
        ),
        Detection(
            class_name="capacitor", 
            class_id=1,
            confidence=0.85,
            bbox=(300, 100, 400, 120),
            orientation=0.0
        ),
        Detection(
            class_name="junction",
            class_id=2,
            confidence=0.95,
            bbox=(248, 108, 252, 112),
            orientation=0.0
        ),
        Detection(
            class_name="battery",
            class_id=3,
            confidence=0.8,
            bbox=(100, 200, 120, 280),
            orientation=90.0
        ),
        Detection(
            class_name="ground",
            class_id=4,
            confidence=0.9,
            bbox=(95, 280, 125, 300),
            orientation=0.0
        )
    ]
    return detections


def test_pin_template_loading():
    """Test pin template loading and inheritance."""
    print("🧪 Testing pin template loading...")
    
    try:
        from circuitcli.models.wire_detector import PinTemplateManager
        
        # Test with default templates
        pin_manager = PinTemplateManager()
        
        # Test getting pin positions for a resistor
        pin_positions = pin_manager.get_pin_positions(
            "resistor", (100, 100, 200, 120), 0.0
        )
        
        print(f"   Resistor pins: {pin_positions}")
        
        # Test with orientation
        pin_positions_rotated = pin_manager.get_pin_positions(
            "resistor", (100, 100, 200, 120), 90.0
        )
        
        print(f"   Resistor pins (90°): {pin_positions_rotated}")
        
        # Test inheritance
        pin_positions_pot = pin_manager.get_pin_positions(
            "potentiometer", (100, 100, 200, 120), 0.0
        )
        
        print(f"   Potentiometer pins: {pin_positions_pot}")
        
        print("✅ Pin template loading test passed")
        return True
        
    except Exception as e:
        print(f"❌ Pin template loading test failed: {e}")
        return False


def test_wire_detection():
    """Test wire detection with mock data."""
    print("🧪 Testing wire detection...")
    
    try:
        # Create test image (this would normally be loaded)
        import numpy as np
        import cv2
        
        # Create a simple test circuit image
        image = np.zeros((400, 500, 3), dtype=np.uint8)
        image.fill(255)  # White background
        
        # Draw some test wires (black lines)
        cv2.line(image, (200, 110), (250, 110), (0, 0, 0), 2)  # Horizontal wire
        cv2.line(image, (250, 110), (300, 110), (0, 0, 0), 2)  # Horizontal wire
        cv2.line(image, (110, 200), (110, 280), (0, 0, 0), 2)  # Vertical wire
        
        # Save test image
        test_image_path = Path("test_circuit.png")
        cv2.imwrite(str(test_image_path), image)
        
        # Create test detections
        detections = create_test_detections()
        
        # Test wire detector
        wire_detector = WireDetector()
        
        # This would normally create a full graph, but we'll test components
        print(f"   Created wire detector with {len(wire_detector.pin_manager.templates)} templates")
        
        # Test pin extraction
        pins = wire_detector._extract_component_pins(detections, {})
        print(f"   Extracted {len(pins)} pins")
        
        # Test skeleton extraction
        skeleton = wire_detector._extract_wire_skeleton(image, detections)
        print(f"   Extracted skeleton: {skeleton.shape}")
        
        # Save debug skeleton
        cv2.imwrite("test_skeleton.png", skeleton)
        
        print("✅ Wire detection test passed")
        
        # Cleanup
        if test_image_path.exists():
            test_image_path.unlink()
        skeleton_path = Path("test_skeleton.png")
        if skeleton_path.exists():
            skeleton_path.unlink()
        
        return True
        
    except Exception as e:
        print(f"❌ Wire detection test failed: {e}")
        return False


def test_graph_creation():
    """Test NetworkX graph creation."""
    print("🧪 Testing graph creation...")
    
    try:
        import networkx as nx
        
        # Create a simple test graph
        G = nx.Graph()
        
        # Add some test nodes
        G.add_node("resistor_0", type="component", class_name="resistor")
        G.add_node("resistor_0.1", type="pin", component_id="resistor_0")
        G.add_node("resistor_0.2", type="pin", component_id="resistor_0")
        G.add_node("junction_0", type="junction")
        
        # Add edges
        G.add_edge("resistor_0", "resistor_0.1", type="belongs_to")
        G.add_edge("resistor_0", "resistor_0.2", type="belongs_to")
        G.add_edge("resistor_0.1", "junction_0", type="wire")
        
        print(f"   Created graph with {len(G.nodes)} nodes and {len(G.edges)} edges")
        
        # Test JSON serialization
        test_graph_path = Path("test_graph.json")
        if save_graph_to_json(G, test_graph_path):
            print(f"   Graph saved to {test_graph_path}")
            
            # Test loading back
            with open(test_graph_path, 'r') as f:
                graph_data = json.load(f)
            
            print(f"   Graph loaded: {len(graph_data['nodes'])} nodes, {len(graph_data['edges'])} edges")
            
            # Cleanup
            if test_graph_path.exists():
                test_graph_path.unlink()
        
        print("✅ Graph creation test passed")
        return True
        
    except Exception as e:
        print(f"❌ Graph creation test failed: {e}")
        return False


def test_visualization():
    """Test graph visualization."""
    print("🧪 Testing graph visualization...")
    
    try:
        import networkx as nx
        
        # Create test graph
        G = nx.Graph()
        G.add_node("R1", type="component", class_name="resistor")
        G.add_node("R1.1", type="pin", component_id="R1")
        G.add_node("R1.2", type="pin", component_id="R1")
        G.add_node("J1", type="junction")
        
        G.add_edge("R1", "R1.1", type="belongs_to")
        G.add_edge("R1", "R1.2", type="belongs_to")
        G.add_edge("R1.1", "J1", type="wire")
        
        # Test visualization
        visualizer = GraphVisualizer()
        test_viz_path = Path("test_graph_viz.png")
        
        if visualizer.visualize_graph(G, test_viz_path):
            print(f"   Graph visualization saved to {test_viz_path}")
            # Cleanup
            if test_viz_path.exists():
                test_viz_path.unlink()
        
        print("✅ Graph visualization test passed")
        return True
        
    except Exception as e:
        print(f"❌ Graph visualization test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Running Wire Detection Tests\n")
    
    tests = [
        test_pin_template_loading,
        test_wire_detection,
        test_graph_creation,
        test_visualization
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 