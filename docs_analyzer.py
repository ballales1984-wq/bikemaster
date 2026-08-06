"""Analyze Python files for missing docstrings and complex logic needing comments.

Scans the BikeMaster project (excluding .venv_check, .venv, node_modules, __pycache__, .git)
and reports:
  - Files missing module-level docstrings
  - Public functions/methods missing docstrings
  - Classes missing docstrings
  - Heuristic flags for complex logic (long functions, nested branches, etc.)
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(r"D:\BikeMaster")
EXCLUDE_DIRS = {".venv_check", ".venv", "node_modules", "__pycache__", ".git", "dist", "build"}


@dataclass
class SymbolInfo:
    name: str
    lineno: int
    kind: str  # "function", "async_function", "class", "method"
    missing_doc: bool = True
    is_public: bool = True
    complexity_flags: list[str] = field(default_factory=list)


@dataclass
class FileReport:
    path: str
    rel_path: str
    has_module_doc: bool
    symbols: list[SymbolInfo] = field(default_factory=list)
    total_lines: int = 0
    complex_logic_flags: list[str] = field(default_factory=list)


def _is_public(name: str) -> bool:
    if name.startswith("__") and name.endswith("__"):
        return False
    return not name.startswith("_")


def _analyze_file(path: Path) -> FileReport | None:
    try:
        source = path.read_text(encoding="utf-8")
    except Exception:
        return None

    rel = path.relative_to(PROJECT_ROOT)
    report = FileReport(path=str(path), rel_path=str(rel), has_module_doc=False)
    report.total_lines = len(source.splitlines())

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return report

    # Module docstring
    if ast.get_docstring(tree):
        report.has_module_doc = True

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            is_public = _is_public(node.name)
            flags: list[str] = []
            if isinstance(node, ast.AsyncFunctionDef):
                flags.append("async")
            doc = ast.get_docstring(node)
            report.symbols.append(
                SymbolInfo(
                    name=node.name,
                    lineno=node.lineno,
                    kind="async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
                    missing_doc=doc is None,
                    is_public=is_public,
                    complexity_flags=flags,
                )
            )
            # Heuristic: long function body
            if node.end_lineno and node.end_lineno - node.lineno > 80:
                flags.append("long_function (>80 lines)")
            # Heuristic: nested try/except blocks
            nested_tries = sum(
                1 for child in ast.walk(node)
                if isinstance(child, ast.Try) and child is not node
            )
            if nested_tries >= 3:
                flags.append("many_nested_tries")
            # Heuristic: many if/elif branches
            if_count = sum(1 for child in ast.walk(node) if isinstance(child, ast.If))
            if if_count >= 5:
                flags.append("many_branches")
        elif isinstance(node, ast.ClassDef):
            is_public = _is_public(node.name)
            doc = ast.get_docstring(node)
            report.symbols.append(
                SymbolInfo(
                    name=node.name,
                    lineno=node.lineno,
                    kind="class",
                    missing_doc=doc is None,
                    is_public=is_public,
                )
            )

    return report


def main() -> None:
    reports: list[FileReport] = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Prune excluded dirs in-place
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            path = Path(root) / fname
            report = _analyze_file(path)
            if report:
                reports.append(report)

    # Sort: files missing module docs first, then by path
    reports.sort(key=lambda r: (r.has_module_doc, r.rel_path.lower()))

    missing_module = [r for r in reports if not r.has_module_doc]
    missing_public_docs = []
    complex_files = []
    for r in reports:
        for s in r.symbols:
            if s.is_public and s.missing_doc:
                missing_public_docs.append((r.rel_path, s))
        if r.complex_logic_flags:
            complex_files.append((r.rel_path, r.complex_logic_flags))

    print(f"Total Python files scanned: {len(reports)}")
    print(f"Files missing module docstring: {len(missing_module)}")
    print(f"Public symbols missing docstrings: {len(missing_public_docs)}")
    print()

    print("=== FILES MISSING MODULE DOCSTRINGS (first 80) ===")
    for r in missing_module[:80]:
        print(f"  {r.rel_path}  ({r.total_lines} lines)")
    if len(missing_module) > 80:
        print(f"  ... and {len(missing_module) - 80} more")

    print()
    print("=== PUBLIC SYMBOLS MISSING DOCSTRINGS (first 80) ===")
    for rel, sym in missing_public_docs[:80]:
        print(f"  {rel}:{sym.lineno}  {sym.kind} {sym.name}")
    if len(missing_public_docs) > 80:
        print(f"  ... and {len(missing_public_docs) - 80} more")

    print()
    print("=== FILES WITH COMPLEX LOGIC HEURISTICS (first 40) ===")
    for rel, flags in complex_files[:40]:
        print(f"  {rel}: {', '.join(flags)}")
    if len(complex_files) > 40:
        print(f"  ... and {len(complex_files) - 40} more")


if __name__ == "__main__":
    main()
