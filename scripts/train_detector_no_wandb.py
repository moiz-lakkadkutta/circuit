#!/usr/bin/env python3
"""Training script for YOLOv8 with W&B explicitly disabled via environment variables."""

import os
import sys

# Disable W&B before importing anything else
os.environ["WANDB_MODE"] = "disabled"
os.environ["WANDB_DISABLED"] = "true"

# Now run the main training script
if __name__ == "__main__":
    # Add --use-wandb false to arguments if not present
    if "--use-wandb" not in sys.argv:
        sys.argv.extend(["--use-wandb", "false"])
    
    # Import additional modules for subprocess execution
    import subprocess
    from pathlib import Path
    
    # Get the current script directory
    script_dir = Path(__file__).parent
    train_script = script_dir / "train_detector.py"
    
    # Run the training script with current arguments
    result = subprocess.run([sys.executable, str(train_script)] + sys.argv[1:])
    sys.exit(result.returncode) 