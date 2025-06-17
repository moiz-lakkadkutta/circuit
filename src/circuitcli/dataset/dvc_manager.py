"""DVC management utilities for dataset versioning and tracking."""

import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class DVCManager:
    """Manages DVC operations for dataset versioning."""
    
    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize DVC manager.
        
        Args:
            repo_root: Root directory of the repository. Defaults to current directory.
        """
        self.repo_root = repo_root or Path.cwd()
        self.data_dir = self.repo_root / "data"
        self.dvc_dir = self.repo_root / ".dvc"
        
    def initialize_dvc(self) -> bool:
        """Initialize DVC repository if not already initialized.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            if not self.dvc_dir.exists():
                console.print("🔧 Initializing DVC repository...")
                result = subprocess.run(
                    ["dvc", "init"], 
                    cwd=self.repo_root, 
                    capture_output=True, 
                    text=True
                )
                if result.returncode != 0:
                    console.print(f"❌ DVC init failed: {result.stderr}")
                    return False
                console.print("✅ DVC repository initialized")
            else:
                console.print("✅ DVC repository already initialized")
            return True
        except Exception as e:
            console.print(f"❌ Error initializing DVC: {e}")
            return False
    
    def add_data_directory(self, data_path: Path) -> bool:
        """Add data directory to DVC tracking.
        
        Args:
            data_path: Path to the data directory to track.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            if not data_path.exists():
                console.print(f"❌ Data directory does not exist: {data_path}")
                return False
                
            console.print(f"📦 Adding {data_path} to DVC tracking...")
            result = subprocess.run(
                ["dvc", "add", str(data_path)],
                cwd=self.repo_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                console.print(f"❌ DVC add failed: {result.stderr}")
                return False
                
            console.print(f"✅ Added {data_path} to DVC tracking")
            return True
            
        except Exception as e:
            console.print(f"❌ Error adding data to DVC: {e}")
            return False
    
    def setup_remote(self, remote_name: str, remote_url: str) -> bool:
        """Set up DVC remote storage.
        
        Args:
            remote_name: Name for the remote.
            remote_url: URL for the remote storage.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            console.print(f"🔗 Setting up DVC remote: {remote_name}")
            
            # Add remote
            result = subprocess.run(
                ["dvc", "remote", "add", remote_name, remote_url],
                cwd=self.repo_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                console.print(f"❌ Failed to add remote: {result.stderr}")
                return False
            
            # Set as default
            result = subprocess.run(
                ["dvc", "remote", "default", remote_name],
                cwd=self.repo_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                console.print(f"❌ Failed to set default remote: {result.stderr}")
                return False
                
            console.print(f"✅ DVC remote {remote_name} configured")
            return True
            
        except Exception as e:
            console.print(f"❌ Error setting up DVC remote: {e}")
            return False
    
    def pull_data(self) -> bool:
        """Pull data from DVC remote.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Pulling data from DVC remote...", total=None)
                
                result = subprocess.run(
                    ["dvc", "pull"],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True
                )
                
                progress.update(task, completed=True)
                
            if result.returncode != 0:
                console.print(f"❌ DVC pull failed: {result.stderr}")
                return False
                
            console.print("✅ Data pulled successfully from DVC remote")
            return True
            
        except Exception as e:
            console.print(f"❌ Error pulling data: {e}")
            return False
    
    def push_data(self) -> bool:
        """Push data to DVC remote.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Pushing data to DVC remote...", total=None)
                
                result = subprocess.run(
                    ["dvc", "push"],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True
                )
                
                progress.update(task, completed=True)
                
            if result.returncode != 0:
                console.print(f"❌ DVC push failed: {result.stderr}")
                return False
                
            console.print("✅ Data pushed successfully to DVC remote")
            return True
            
        except Exception as e:
            console.print(f"❌ Error pushing data: {e}")
            return False
    
    def create_pipeline_stage(self, stage_name: str, config: Dict[str, Any]) -> bool:
        """Create a DVC pipeline stage.
        
        Args:
            stage_name: Name of the pipeline stage.
            config: Stage configuration dictionary.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            dvc_yaml_path = self.repo_root / "dvc.yaml"
            
            # Load existing dvc.yaml or create new
            if dvc_yaml_path.exists():
                with open(dvc_yaml_path, 'r') as f:
                    dvc_config = yaml.safe_load(f) or {}
            else:
                dvc_config = {}
            
            # Add stages section if not exists
            if 'stages' not in dvc_config:
                dvc_config['stages'] = {}
                
            # Add the new stage
            dvc_config['stages'][stage_name] = config
            
            # Write back to file
            with open(dvc_yaml_path, 'w') as f:
                yaml.dump(dvc_config, f, default_flow_style=False, indent=2)
                
            console.print(f"✅ Added DVC pipeline stage: {stage_name}")
            return True
            
        except Exception as e:
            console.print(f"❌ Error creating pipeline stage: {e}")
            return False 