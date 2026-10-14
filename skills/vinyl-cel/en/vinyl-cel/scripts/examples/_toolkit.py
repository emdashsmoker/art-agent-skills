"""Locates the codeillust package for the example scenes.

A copied scene script finds the toolkit through CODEILLUST_HOME (the skill's
scripts folder); inside the skill the parent folder is used.
"""
import os
import sys
from pathlib import Path

TOOLKIT_DIR = Path(os.environ.get("CODEILLUST_HOME", Path(__file__).resolve().parent.parent))
if not (TOOLKIT_DIR / "codeillust").is_dir():
    sys.exit("codeillust package not found. Set CODEILLUST_HOME to the skill's scripts folder.")
if str(TOOLKIT_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLKIT_DIR))
