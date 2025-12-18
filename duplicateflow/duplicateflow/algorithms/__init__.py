"""
DuplicateFlow Algorithms auto-discovery.
"""
from pathlib import Path
import importlib

_algorithm_dir = Path(__file__).parent
for file in sorted(_algorithm_dir.glob("*.py")):
    if file.name.startswith("_") or file.stem == "base":
        continue
    try:
        importlib.import_module(f"duplicateflow.algorithms.{file.stem}")
    except Exception as e:
        print(f"Warning: Failed to load {file.stem}: {e}")

from duplicateflow.core import list_algorithms, get_algorithm, get_algorithm_names
__all__ = ["list_algorithms", "get_algorithm", "get_algorithm_names"]

