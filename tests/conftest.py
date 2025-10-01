"""
Test configuration for SD Emulation GUI

This module configures the test environment and sets up proper paths
for importing modules during testing.
"""

import sys
import os
from pathlib import Path

# Add the src directory to sys.path so tests can import the main modules
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sd_emulation_gui_path = src_path / "sd_emulation_gui"
app_path = sd_emulation_gui_path / "app"

# Add paths in correct order
paths_to_add = [
    str(app_path),  # For importing app modules
    str(sd_emulation_gui_path),  # For importing sd_emulation_gui modules
    str(src_path),  # For importing src modules
    str(project_root),  # For importing from project root
    str(project_root / "meta" / "config"),  # For path configuration
]

for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)

# Set environment variables for testing
os.environ["PYTHONPATH"] = str(src_path)

print("Test configuration loaded:")
print(f"  Project root: {project_root}")
print(f"  App path: {app_path}")
print(f"  SD Emulation GUI path: {sd_emulation_gui_path}")
print(f"  Src path: {src_path}")
print(f"  Meta config path: {project_root}/meta/config")
print(f"  PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
print(f"  First 5 sys.path entries: {sys.path[:5]}")
