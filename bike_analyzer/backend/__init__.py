"""Backend package."""

import importlib
import importlib.util
import sys
from pathlib import Path

try:
    importlib.import_module("bike_analyzer.backend.settings")
except PermissionError:
    _spec = importlib.util.spec_from_file_location(
        "bike_analyzer.backend.settings",
        str(Path(__file__).parent / "settings.py.new"),
    )
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules["bike_analyzer.backend.settings"] = _mod
    _spec.loader.exec_module(_mod)
