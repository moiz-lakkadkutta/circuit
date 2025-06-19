"""Wire Detection and Graph Assembly for Electrical Circuits."""

import cv2
import numpy as np
import networkx as nx
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Set
import yaml
import json
from dataclasses import dataclass
from rich.console import Console
from rich.progress import track
import math

console = Console()


@dataclass
class Detection:
    """Represents a YOLO detection result."""
    class_name: str
    class_id: int
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    mask: Optional[np.ndarray] = None
    orientation: float = 0.0  # degrees


@dataclass
class Pin:
    """Represents a component pin with world coordinates."""
    component_id: str
    pin_id: str
    position: Tuple[float, float]  # (x, y) in image coordinates
    component_class: str


@dataclass
class Junction:
    """Represents a wire junction point."""
    position: Tuple[float, float]
    junction_id: str
    connected_wires: List[str]


class PinTemplateManager:
    """Manages component pin templates and orientation transformations."""
    
    def __init__(self, templates_path: Path = None):
        """Initialize pin template manager.
        
        Args:
            templates_path: Path to pin templates YAML file
        """
        self.templates_path = templates_path or Path("config/pin_templates.yaml")
        self.templates = self._load_templates()
        
    def _load_templates(self) -> Dict[str, Any]:
        """Load pin templates from YAML file."""
        try:
            with open(self.templates_path, 'r') as f:
                templates = yaml.safe_load(f)
            
            # Resolve inheritance
            resolved_templates = {}
            for component_name, template in templates.items():
                resolved_templates[component_name] = self._resolve_inheritance(
                    template, templates
                )
            
            console.print(f"📍 Loaded {len(resolved_templates)} pin templates")
            return resolved_templates
            
        except Exception as e:
            console.print(f"❌ Error loading pin templates: {e}")
            return {}
    
    def _resolve_inheritance(self, template: Dict[str, Any], 
                           all_templates: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve template inheritance."""
        if 'inherit' not in template:
            return template
        
        parent_name = template['inherit']
        if parent_name not in all_templates:
            console.print(f"⚠️  Warning: Parent template '{parent_name}' not found")
            return template
        
        parent_template = self._resolve_inheritance(
            all_templates[parent_name], all_templates
        )
        
        # Merge parent and child templates
        resolved = parent_template.copy()
        for key, value in template.items():
            if key != 'inherit':
                resolved[key] = value
        
        return resolved
    
    def get_pin_positions(self, component_class: str, bbox: Tuple[int, int, int, int],
                         orientation: float = 0.0) -> List[Tuple[str, Tuple[float, float]]]:
        """Get absolute pin positions for a component.
        
        Args:
            component_class: Component class name
            bbox: Bounding box (x1, y1, x2, y2)
            orientation: Component orientation in degrees
            
        Returns:
            List of (pin_id, (x, y)) tuples
        """
        if component_class not in self.templates:
            console.print(f"⚠️  Warning: No template found for '{component_class}'")
            return []
        
        template = self.templates[component_class]
        pins = template.get('pins', [])
        
        if not pins:
            return []
        
        # Calculate component center and dimensions
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        half_width = (x2 - x1) / 2
        half_height = (y2 - y1) / 2
        
        # Convert orientation to radians
        angle_rad = math.radians(orientation)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        pin_positions = []
        for pin_info in pins:
            pin_id = pin_info['id']
            rel_x, rel_y = pin_info['pos']
            
            # Scale relative position by bbox dimensions
            scaled_x = rel_x * half_width
            scaled_y = rel_y * half_height
            
            # Apply rotation
            rotated_x = scaled_x * cos_a - scaled_y * sin_a
            rotated_y = scaled_x * sin_a + scaled_y * cos_a
            
            # Translate to absolute position
            abs_x = center_x + rotated_x
            abs_y = center_y + rotated_y
            
            pin_positions.append((pin_id, (abs_x, abs_y)))
        
        return pin_positions


class WireDetector:
    """Detects wires and creates circuit graph from image and component detections."""
    
    def __init__(self, pin_templates_path: Path = None):
        """Initialize wire detector.
        
        Args:
            pin_templates_path: Path to pin templates configuration
        """
        self.pin_manager = PinTemplateManager(pin_templates_path)
        self.debug_images = {}  # Store intermediate images for debugging
        
    def create_circuit_graph(self, image_path: Path, detections: List[Detection],
                           orientations: Dict[str, float] = None) -> nx.Graph:
        """Create NetworkX graph from image and detections.
        
        Args:
            image_path: Path to circuit image
            detections: List of component detections
            orientations: Component orientations {detection_idx: angle_degrees}
            
        Returns:
            NetworkX graph representing the circuit
        """
        console.print("🔗 Creating circuit graph...")
        
        # Load image
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        # Step 1: Extract wire skeleton
        wire_skeleton = self._extract_wire_skeleton(image, detections)
        
        # Step 2: Get component pins
        pins = self._extract_component_pins(detections, orientations or {})
        
        # Step 3: Find junctions
        junctions = self._find_junctions(wire_skeleton, detections)
        
        # Step 4: Trace wire connections
        connections = self._trace_wire_connections(wire_skeleton, pins, junctions, detections)
        
        # Step 5: Build NetworkX graph
        graph = self._build_networkx_graph(detections, pins, junctions, connections)
        
        console.print(f"✅ Circuit graph created:")
        console.print(f"   Nodes: {len(graph.nodes)}")
        console.print(f"   Edges: {len(graph.edges)}")
        
        return graph
    
    def _extract_wire_skeleton(self, image: np.ndarray, 
                             detections: List[Detection]) -> np.ndarray:
        """Extract wire skeleton from image by masking components.
        
        Args:
            image: Input circuit image
            detections: Component detections to mask out
            
        Returns:
            Binary skeleton image
        """
        console.print("🏗️  Extracting wire skeleton...")
        
        # Create mask for components
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        
        for detection in detections:
            x1, y1, x2, y2 = detection.bbox
            # Add some padding around components
            padding = 5
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(image.shape[1], x2 + padding)
            y2 = min(image.shape[0], y2 + padding)
            
            mask[y1:y2, x1:x2] = 255
        
        # Inpaint components to get clean wire image
        wire_image = cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)
        
        # Convert to grayscale
        gray = cv2.cvtColor(wire_image, cv2.COLOR_BGR2GRAY)
        
        # Apply Canny edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Morphological operations to clean up edges
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        # Skeletonization (thinning)
        skeleton = self._skeletonize(edges)
        
        # Store debug images
        self.debug_images.update({
            'original': image,
            'component_mask': mask,
            'wire_image': wire_image,
            'edges': edges,
            'skeleton': skeleton
        })
        
        return skeleton
    
    def _skeletonize(self, binary_image: np.ndarray) -> np.ndarray:
        """Apply skeletonization to binary image using Zhang-Suen algorithm."""
        # Convert to binary (0/1)
        skeleton = (binary_image > 0).astype(np.uint8)
        
        def neighbors(x, y, image):
            """Get 8-neighborhood values in clockwise order starting from top"""
            return [image[x-1,y], image[x-1,y+1], image[x,y+1], image[x+1,y+1],
                    image[x+1,y], image[x+1,y-1], image[x,y-1], image[x-1,y-1]]
        
        def transitions(neighbors):
            """Count 0-1 transitions in neighborhood"""
            n = neighbors + neighbors[0:1]  # Wrap around
            return sum((n1, n2) == (0, 1) for n1, n2 in zip(n, n[1:]))
        
        changed = True
        while changed:
            changed = False
            
            # Step 1
            to_remove = []
            for x in range(1, skeleton.shape[0] - 1):
                for y in range(1, skeleton.shape[1] - 1):
                    if skeleton[x, y] == 1:
                        n = neighbors(x, y, skeleton)
                        if (2 <= sum(n) <= 6 and 
                            transitions(n) == 1 and
                            n[0] * n[2] * n[4] == 0 and
                            n[2] * n[4] * n[6] == 0):
                            to_remove.append((x, y))
            
            for x, y in to_remove:
                skeleton[x, y] = 0
                changed = True
            
            # Step 2
            to_remove = []
            for x in range(1, skeleton.shape[0] - 1):
                for y in range(1, skeleton.shape[1] - 1):
                    if skeleton[x, y] == 1:
                        n = neighbors(x, y, skeleton)
                        if (2 <= sum(n) <= 6 and 
                            transitions(n) == 1 and
                            n[0] * n[2] * n[6] == 0 and
                            n[0] * n[4] * n[6] == 0):
                            to_remove.append((x, y))
            
            for x, y in to_remove:
                skeleton[x, y] = 0
                changed = True
        
        return (skeleton * 255).astype(np.uint8)
    
    def _extract_component_pins(self, detections: List[Detection],
                              orientations: Dict[int, float]) -> List[Pin]:
        """Extract component pin locations."""
        pins = []
        
        for i, detection in enumerate(detections):
            component_id = f"{detection.class_name}_{i}"
            orientation = orientations.get(i, 0.0)
            
            pin_positions = self.pin_manager.get_pin_positions(
                detection.class_name, detection.bbox, orientation
            )
            
            for pin_id, position in pin_positions:
                pin = Pin(
                    component_id=component_id,
                    pin_id=pin_id,
                    position=position,
                    component_class=detection.class_name
                )
                pins.append(pin)
        
        console.print(f"📍 Extracted {len(pins)} component pins")
        return pins
    
    def _find_junctions(self, skeleton: np.ndarray, 
                       detections: List[Detection]) -> List[Junction]:
        """Find wire junctions from skeleton."""
        junctions = []
        
        # Find junctions from detected junction components
        junction_detections = [d for d in detections if d.class_name == 'junction']
        for i, detection in enumerate(junction_detections):
            x1, y1, x2, y2 = detection.bbox
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            
            junction = Junction(
                position=(center_x, center_y),
                junction_id=f"junction_{i}",
                connected_wires=[]
            )
            junctions.append(junction)
        
        # Find junctions from skeleton branch points (≥3 connections)
        branch_points = self._find_branch_points(skeleton)
        
        # Filter out crossovers
        crossover_boxes = [d.bbox for d in detections if d.class_name == 'crossover']
        
        for i, (x, y) in enumerate(branch_points):
            # Check if this branch point is inside a crossover
            is_crossover = False
            for x1, y1, x2, y2 in crossover_boxes:
                if x1 <= x <= x2 and y1 <= y <= y2:
                    is_crossover = True
                    break
            
            if not is_crossover:
                junction = Junction(
                    position=(float(x), float(y)),
                    junction_id=f"branch_{len(junctions) + i}",
                    connected_wires=[]
                )
                junctions.append(junction)
        
        console.print(f"🔗 Found {len(junctions)} junctions")
        return junctions
    
    def _find_branch_points(self, skeleton: np.ndarray) -> List[Tuple[int, int]]:
        """Find branch points in skeleton (points with ≥3 neighbors)."""
        branch_points = []
        rows, cols = skeleton.shape
        
        for y in range(1, rows - 1):
            for x in range(1, cols - 1):
                if skeleton[y, x] > 0:  # On skeleton
                    # Count neighbors
                    neighbors = 0
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            if dx == 0 and dy == 0:
                                continue
                            if skeleton[y + dy, x + dx] > 0:
                                neighbors += 1
                    
                    # Branch point if ≥3 neighbors
                    if neighbors >= 3:
                        branch_points.append((x, y))
        
        return branch_points
    
    def _trace_wire_connections(self, skeleton: np.ndarray, pins: List[Pin],
                              junctions: List[Junction], 
                              detections: List[Detection]) -> List[Tuple[str, str]]:
        """Trace wire connections between pins and junctions."""
        connections = []
        
        # Create lists of all connection points
        connection_points = []
        
        # Add pins
        for pin in pins:
            connection_points.append({
                'id': f"{pin.component_id}.{pin.pin_id}",
                'position': pin.position,
                'type': 'pin'
            })
        
        # Add junctions
        for junction in junctions:
            connection_points.append({
                'id': junction.junction_id,
                'position': junction.position,
                'type': 'junction'
            })
        
        # For each pair of connection points, check if they're connected by wire
        for i in range(len(connection_points)):
            for j in range(i + 1, len(connection_points)):
                point1 = connection_points[i]
                point2 = connection_points[j]
                
                if self._are_connected_by_wire(skeleton, point1['position'], 
                                              point2['position']):
                    connections.append((point1['id'], point2['id']))
        
        console.print(f"🔌 Found {len(connections)} wire connections")
        return connections
    
    def _are_connected_by_wire(self, skeleton: np.ndarray, 
                              pos1: Tuple[float, float], 
                              pos2: Tuple[float, float]) -> bool:
        """Check if two points are connected by a wire path in skeleton."""
        from collections import deque
        
        # Convert to integer coordinates
        x1, y1 = int(pos1[0]), int(pos1[1])
        x2, y2 = int(pos2[0]), int(pos2[1])
        
        # Check bounds
        rows, cols = skeleton.shape
        if not (0 <= x1 < cols and 0 <= y1 < rows and 
                0 <= x2 < cols and 0 <= y2 < rows):
            return False
        
        # Find nearest skeleton points
        start_point = self._find_nearest_skeleton_point(skeleton, (x1, y1))
        end_point = self._find_nearest_skeleton_point(skeleton, (x2, y2))
        
        if start_point is None or end_point is None:
            return False
        
        # BFS to find path
        queue = deque([start_point])
        visited = set([start_point])
        
        while queue:
            x, y = queue.popleft()
            
            if (x, y) == end_point:
                return True
            
            # Check 8-connected neighbors
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    
                    nx, ny = x + dx, y + dy
                    if (0 <= nx < cols and 0 <= ny < rows and 
                        skeleton[ny, nx] > 0 and (nx, ny) not in visited):
                        visited.add((nx, ny))
                        queue.append((nx, ny))
        
        return False
    
    def _find_nearest_skeleton_point(self, skeleton: np.ndarray, 
                                   point: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """Find nearest skeleton point to given point."""
        x, y = point
        rows, cols = skeleton.shape
        
        # Search in expanding circles
        for radius in range(1, 50):  # Max search radius
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if dx*dx + dy*dy <= radius*radius:
                        nx, ny = x + dx, y + dy
                        if (0 <= nx < cols and 0 <= ny < rows and 
                            skeleton[ny, nx] > 0):
                            return (nx, ny)
        
        return None
    
    def _build_networkx_graph(self, detections: List[Detection], pins: List[Pin],
                            junctions: List[Junction], 
                            connections: List[Tuple[str, str]]) -> nx.Graph:
        """Build NetworkX graph from extracted components."""
        G = nx.Graph()
        
        # Add component super-nodes
        for i, detection in enumerate(detections):
            component_id = f"{detection.class_name}_{i}"
            G.add_node(component_id, 
                      type='component',
                      class_name=detection.class_name,
                      bbox=detection.bbox,
                      confidence=detection.confidence)
        
        # Add pin sub-nodes
        for pin in pins:
            pin_node_id = f"{pin.component_id}.{pin.pin_id}"
            G.add_node(pin_node_id,
                      type='pin',
                      component_id=pin.component_id,
                      pin_id=pin.pin_id,
                      position=pin.position,
                      component_class=pin.component_class)
            
            # Connect pin to component super-node
            G.add_edge(pin.component_id, pin_node_id, type='belongs_to')
        
        # Add junction nodes
        for junction in junctions:
            G.add_node(junction.junction_id,
                      type='junction',
                      position=junction.position)
        
        # Add wire connections
        for node1_id, node2_id in connections:
            G.add_edge(node1_id, node2_id, type='wire')
        
        return G
    
    def save_debug_images(self, output_dir: Path):
        """Save debug images for inspection."""
        output_dir.mkdir(exist_ok=True, parents=True)
        
        for name, image in self.debug_images.items():
            output_path = output_dir / f"debug_{name}.png"
            cv2.imwrite(str(output_path), image)
        
        console.print(f"💾 Debug images saved to {output_dir}")


class GraphVisualizer:
    """Visualizes circuit graphs using matplotlib."""
    
    def visualize_graph(self, graph: nx.Graph, output_path: Path, 
                       layout: str = 'spring') -> bool:
        """Visualize NetworkX graph and save as image."""  
        try:
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(12, 8))
            
            # Choose layout
            if layout == 'spring':
                pos = nx.spring_layout(graph, k=3, iterations=50)
            elif layout == 'circular':
                pos = nx.circular_layout(graph)
            elif layout == 'shell':
                pos = nx.shell_layout(graph)
            else:
                pos = nx.spring_layout(graph)
            
            # Draw different node types with different colors
            component_nodes = [n for n, d in graph.nodes(data=True) if d.get('type') == 'component']
            pin_nodes = [n for n, d in graph.nodes(data=True) if d.get('type') == 'pin']
            junction_nodes = [n for n, d in graph.nodes(data=True) if d.get('type') == 'junction']
            
            # Draw nodes
            if component_nodes:
                nx.draw_networkx_nodes(graph, pos, nodelist=component_nodes, 
                                     node_color='lightblue', node_size=800, alpha=0.8)
            if pin_nodes:
                nx.draw_networkx_nodes(graph, pos, nodelist=pin_nodes,
                                     node_color='orange', node_size=200, alpha=0.8)
            if junction_nodes:
                nx.draw_networkx_nodes(graph, pos, nodelist=junction_nodes,
                                     node_color='red', node_size=300, alpha=0.8)
            
            # Draw edges with different colors for different types
            wire_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get('type') == 'wire']
            belongs_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get('type') == 'belongs_to']
            
            if wire_edges:
                nx.draw_networkx_edges(graph, pos, edgelist=wire_edges, 
                                     edge_color='black', width=2)
            if belongs_edges:
                nx.draw_networkx_edges(graph, pos, edgelist=belongs_edges,
                                     edge_color='gray', width=1, style='dashed')
            
            # Add labels
            labels = {}
            for node, data in graph.nodes(data=True):
                if data.get('type') == 'component':
                    labels[node] = data.get('class_name', node)
                else:
                    labels[node] = node.split('.')[-1] if '.' in node else node
            
            nx.draw_networkx_labels(graph, pos, labels, font_size=8)
            
            plt.title("Circuit Graph Visualization")
            plt.axis('off')
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            console.print(f"📊 Graph visualization saved to {output_path}")
            return True
            
        except Exception as e:
            console.print(f"❌ Error visualizing graph: {e}")
            return False


def load_detections_from_json(json_path: Path) -> List[Detection]:
    """Load detections from YOLO JSON output."""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        detections = []
        for item in data:
            detection = Detection(
                class_name=item['class_name'],
                class_id=item['class_id'],
                confidence=item['confidence'],
                bbox=tuple(item['bbox']),
                orientation=item.get('orientation', 0.0)
            )
            detections.append(detection)
        
        console.print(f"📥 Loaded {len(detections)} detections")
        return detections
        
    except Exception as e:
        console.print(f"❌ Error loading detections: {e}")
        return []


def save_graph_to_json(graph: nx.Graph, output_path: Path) -> bool:
    """Save NetworkX graph to JSON format."""
    try:
        # Convert graph to JSON-serializable format
        graph_data = {
            'nodes': [],
            'edges': []
        }
        
        # Add nodes
        for node_id, data in graph.nodes(data=True):
            node_data = {'id': node_id}
            node_data.update(data)
            graph_data['nodes'].append(node_data)
        
        # Add edges
        for u, v, data in graph.edges(data=True):
            edge_data = {'source': u, 'target': v}
            edge_data.update(data)
            graph_data['edges'].append(edge_data)
        
        # Save to JSON
        with open(output_path, 'w') as f:
            json.dump(graph_data, f, indent=2, default=str)
        
        console.print(f"💾 Graph saved to {output_path}")
        return True
        
    except Exception as e:
        console.print(f"❌ Error saving graph: {e}")
        return False 