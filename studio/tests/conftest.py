import os
import sys
import tempfile
from pathlib import Path

# every test run gets its own throwaway data folder; must be set before app imports
os.environ["STUDIO_DATA"] = tempfile.mkdtemp(prefix="studio-test-")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
