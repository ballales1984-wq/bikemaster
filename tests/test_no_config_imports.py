"""Test that no module in bike_analyzer imports the legacy config.py."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BIKE_ANALYZER_DIR = ROOT / "bike_analyzer"


def _is_legacy_config_import(module: str) -> bool:
    """Return True if the import refers to the removed bike_analyzer.backend.config."""
    if not module:
        return False
    parts = module.split(".")
    if parts[-1] != "config":
        return False
    if module in {"logging.config", "unittest.config"}:
        return False
    if module.startswith("bike_analyzer.backend.config"):
        return True
    return module == "config" or module.endswith(".config")


@pytest.mark.parametrize("py_file", list(BIKE_ANALYZER_DIR.rglob("*.py")))
def test_no_legacy_config_import(py_file: Path):
    """Ensure no Python file under bike_analyzer/ imports from legacy config.py."""
    relative = py_file.relative_to(ROOT)
    source = py_file.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if _is_legacy_config_import(module):
                pytest.fail(
                    f"{relative} still imports from legacy config module: {module}"
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if _is_legacy_config_import(alias.name):
                    pytest.fail(
                        f"{relative} still imports legacy config module: {alias.name}"
                    )
