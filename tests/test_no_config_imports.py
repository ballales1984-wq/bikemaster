"""Test that no module in bike_analyzer imports the legacy config.py."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BIKE_ANALYZER_DIR = ROOT / "bike_analyzer"


def _is_legacy_config_import(module: str, level: int = 0) -> bool:
    """Return True if the import refers to the removed bike_analyzer.backend.config.

    Sub-package config modules (e.g. ``sync.config``, ``load_manager.config``)
    imported relatively (``from .config import ...``) are legitimate and must
    not be flagged.
    """
    if not module:
        return False
    parts = module.split(".")
    if parts[-1] != "config":
        return False
    if level > 0:
        return False
    if module in {"logging.config", "unittest.config", "alembic.config"}:
        return False
    if module == "bike_analyzer.backend.config":
        return True
    if module == "config":
        return True
    return module.startswith("bike_analyzer.backend.config.")


@pytest.mark.parametrize("py_file", list(BIKE_ANALYZER_DIR.rglob("*.py")))
def test_no_legacy_config_import(py_file: Path):
    """Ensure no Python file under bike_analyzer/ imports from legacy config.py."""
    relative = py_file.relative_to(ROOT)
    try:
        source = py_file.read_text(encoding="utf-8")
    except PermissionError:
        pytest.skip(f"Cannot read {relative}: permission denied")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if _is_legacy_config_import(module, node.level):
                pytest.fail(
                    f"{relative} still imports from legacy config module: {module}"
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if _is_legacy_config_import(alias.name):
                    pytest.fail(
                        f"{relative} still imports legacy config module: {alias.name}"
                    )
