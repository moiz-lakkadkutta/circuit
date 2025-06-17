"""Constants for dataset preparation and electrical component classes."""

from typing import Dict, List

# Electrical component classes (45 symbol classes as specified in README)
ELECTRICAL_COMPONENTS: Dict[str, List[str]] = {
    # Basic passive components
    "resistor": ["resistor", "variable_resistor", "potentiometer"],
    "capacitor": ["capacitor", "electrolytic_capacitor", "variable_capacitor"],
    "inductor": ["inductor", "variable_inductor", "transformer"],
    
    # Sources
    "voltage_source": ["dc_voltage", "ac_voltage", "battery"],
    "current_source": ["dc_current", "ac_current"],
    
    # Semiconductor devices
    "diode": ["diode", "zener_diode", "led", "photodiode"],
    "transistor": ["npn_bjt", "pnp_bjt", "nmos", "pmos", "jfet"],
    
    # Operational amplifiers
    "opamp": ["opamp", "comparator", "buffer"],
    
    # Digital logic gates
    "logic_gates": ["and_gate", "or_gate", "not_gate", "nand_gate", "nor_gate", "xor_gate"],
    
    # Switches and relays
    "switches": ["switch", "relay", "push_button"],
    
    # Measuring instruments
    "instruments": ["voltmeter", "ammeter", "oscilloscope"],
    
    # Connection elements
    "connections": ["wire", "junction", "crossover", "terminal", "ground"],
    
    # Complex components
    "integrated_circuits": ["timer_555", "microcontroller", "memory"],
    
    # Miscellaneous
    "misc": ["fuse", "crystal", "antenna", "speaker", "microphone"]
}

# Flatten the component list for COCO categories
ALL_COMPONENT_CLASSES = []
for category, components in ELECTRICAL_COMPONENTS.items():
    ALL_COMPONENT_CLASSES.extend(components)

# Add the special connection elements
ALL_COMPONENT_CLASSES.extend(["junction", "crossover", "terminal"])

# Dataset configuration
DATASET_CONFIG = {
    "train_split": 0.7,
    "val_split": 0.2,
    "test_split": 0.1,
    "random_seed": 42,
    "min_bbox_area": 100,  # Minimum bounding box area in pixels
    "max_image_size": (1920, 1080),  # Maximum image dimensions
    "supported_formats": [".jpg", ".jpeg", ".png", ".bmp", ".tiff"],
}

# COCO dataset structure
COCO_INFO = {
    "description": "CircuitCLI Electrical Component Dataset",
    "url": "https://github.com/your-org/circuitcli",
    "version": "1.0",
    "year": 2024,
    "contributor": "CircuitCLI Team",
    "date_created": "2024-01-01"
}

# Augmentation parameters
AUGMENTATION_CONFIG = {
    "brightness_limit": 0.2,
    "contrast_limit": 0.2,
    "blur_limit": 3,
    "noise_limit": 0.1,
    "rotation_limit": 15,
    "scale_limit": 0.1,
    "perspective_limit": 0.05,
} 