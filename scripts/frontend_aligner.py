#!/usr/bin/env python3
"""Frontend alignment tool: PC (Vue/Tauri) source of truth vs Android (Kotlin).

This script supports the "frontend alignment agent". It:
  1. Snapshots the PC frontend tree (routes + key components + hash fingerprints).
  2. Compares it with the previous snapshot to detect what changed between versions.
  3. Cross-references docs/frontend-alignment-map.md to decide which changes must be
     propagated to the Android mobile frontend.
  4. Emits a drift report (JSON + human readable) listing aligned/drift/pc-only items
     and the concrete actions the agent should take.

Usage:
  python scripts/frontend_aligner.py snapshot   # write a new PC snapshot
  python scripts/frontend_aligner.py diff       # compare last snapshot vs current PC
  python scripts/frontend_aligner.py report     # full drift report (snapshot + diff)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "src"
SNAPSHOT_PATH = ROOT / "docs" / "frontend-alignment-snapshot.json"
MAP_PATH = ROOT / "docs" / "frontend-alignment-map.md"

# Files that define the PC feature surface the agent cares about.
PC_ROUTES_FILE = FRONTEND / "router" / "index.ts"
PC_VIEWS = FRONTEND / "views"
PC_COMPONENTS = FRONTEND / "components"

# Statuses used by the map.
ALIGNED = "aligned"
DRIFT = "drift"
PC_ONLY = "pc-only"
MOBILE_ONLY = "mobile-only"


@dataclass
class Feature:
    name: str
    pc_file: str
    mobile: str
    status: str
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "pc_file": self.pc_file,
            "mobile": self.mobile,
            "status": self.status,
            "note": self.note,
        }


# ---- snapshot -----------------------------------------------------------------


def _hash_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    except OSError:
        return ""


def _list_vue(dir_path: Path) -> list[Path]:
    if not dir_path.exists():
        return []
    return sorted(dir_path.rglob("*.vue"))


def _route_names() -> list[str]:
    if not PC_ROUTES_FILE.exists():
        return []
    text = PC_ROUTES_FILE.read_text(encoding="utf-8")
    return re.findall(r'name:\s*"([^"]+)"', text)


def build_snapshot() -> dict[str, Any]:
    routes = _route_names()
    views = {p.stem: _hash_file(p) for p in _list_vue(PC_VIEWS)}
    components = {p.stem: _hash_file(p) for p in _list_vue(PC_COMPONENTS)}
    return {
        "routes": routes,
        "views": views,
        "components": components,
    }


def write_snapshot() -> dict[str, Any]:
    snap = build_snapshot()
    snap["_version"] = "1"
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(
        json.dumps(snap, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[aligner] snapshot written: {SNAPSHOT_PATH}")
    print(
        f"[aligner] {len(snap['routes'])} routes, "
        f"{len(snap['views'])} views, {len(snap['components'])} components"
    )
    return snap


# ---- map parsing --------------------------------------------------------------


def parse_map() -> list[Feature]:
    if not MAP_PATH.exists():
        return []
    text = MAP_PATH.read_text(encoding="utf-8")
    features: list[Feature] = []
    # Match table rows: | name | pc_file | mobile | status | note |
    row_re = re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.*?)\s*\|$")
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        m = row_re.match(line)
        if not m:
            continue
        name, pc_file, mobile, status, note = m.groups()
        if name.strip() in ("PC route / componente", ""):
            continue
        if set(name.strip()) <= set("-"):
            continue
        features.append(
            Feature(
                name=name.strip(),
                pc_file=pc_file.strip(),
                mobile=mobile.strip(),
                status=status.strip(),
                note=note.strip(),
            )
        )
    return features


# ---- diff ---------------------------------------------------------------------


def load_prev_snapshot() -> dict[str, Any] | None:
    if not SNAPSHOT_PATH.exists():
        return None
    try:
        return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def diff_snapshots(prev: dict[str, Any], cur: dict[str, Any]) -> dict[str, Any]:
    changes: dict[str, Any] = {"added": [], "removed": [], "modified": []}

    # `routes` is a list of names; the rest are name->hash dicts.
    def categorize_list(section: str) -> None:
        p = set(prev.get(section, []))
        c = set(cur.get(section, []))
        for key in sorted(c - p):
            changes["added"].append(f"{section}:{key}")
        for key in sorted(p - c):
            changes["removed"].append(f"{section}:{key}")

    def categorize_map(section: str) -> None:
        p = prev.get(section, {})
        c = cur.get(section, {})
        for key in sorted(set(c) - set(p)):
            changes["added"].append(f"{section}:{key}")
        for key in sorted(set(p) - set(c)):
            changes["removed"].append(f"{section}:{key}")
        for key in sorted(set(p) & set(c)):
            if p[key] != c[key]:
                changes["modified"].append(f"{section}:{key}")

    categorize_list("routes")
    categorize_map("views")
    categorize_map("components")
    return changes


# ---- report -------------------------------------------------------------------


@dataclass
class Action:
    feature: str
    status: str
    action: str
    detail: str


def build_actions(changes: dict[str, Any], features: list[Feature]) -> list[Action]:
    actions: list[Action] = []
    feat_by_pc = {f.pc_file: f for f in features}
    # Route/component name -> feature lookup (best effort by substring).
    feat_by_token: dict[str, Feature] = {}
    for f in features:
        for tok in re.findall(r"[A-Za-z0-9_]+", f.pc_file):
            if len(tok) > 3:
                feat_by_token.setdefault(tok.lower(), f)

    def match(token: str) -> Feature | None:
        return feat_by_token.get(token.lower())

    for item in changes["added"] + changes["modified"]:
        section, _, token = item.partition(":")
        feat = match(token)
        if feat is None:
            actions.append(
                Action(token, "unknown", "review", f"Nuovo/modificato {item}; mappalo in frontend-alignment-map.md")
            )
            continue
        if feat.status in (ALIGNED, DRIFT):
            actions.append(
                Action(
                    feat.name,
                    feat.status,
                    "propagate",
                    f"{item} cambiato sul PC -> aggiorna {feat.mobile}",
                )
            )
        elif feat.status == PC_ONLY:
            actions.append(
                Action(
                    feat.name,
                    feat.status,
                    "candidate",
                    f"{item} cambiato sul PC -> candidato al porting su mobile (chiedi conferma)",
                )
            )
    return actions


def print_report(snap: dict[str, Any], changes: dict[str, Any], actions: list[Action]) -> None:
    print("=" * 72)
    print("FRONTEND ALIGNMENT REPORT  (PC source of truth -> Android mobile)")
    print("=" * 72)
    print(f"Routes: {len(snap['routes'])}  Views: {len(snap['views'])}  Components: {len(snap['components'])}")
    print("-" * 72)
    print("Drift vs previous snapshot:")
    print(f"  added:    {changes['added'] or 'none'}")
    print(f"  removed:  {changes['removed'] or 'none'}")
    print(f"  modified: {changes['modified'] or 'none'}")
    print("-" * 72)
    print("Actions for the agent:")
    if not actions:
        print("  (nessun cambiamento rilevato — i frontend sono allineati)")
    for a in actions:
        print(f"  [{a.status:8}] {a.action:9} {a.feature}: {a.detail}")
    print("=" * 72)


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "report"
    if cmd == "snapshot":
        write_snapshot()
        return 0
    if cmd == "diff":
        prev = load_prev_snapshot()
        cur = build_snapshot()
        if prev is None:
            print("[aligner] nessuno snapshot precedente; esegui `snapshot` prima.")
            return 1
        changes = diff_snapshots(prev, cur)
        print(json.dumps(changes, indent=2, ensure_ascii=False))
        return 0
    if cmd == "report":
        prev = load_prev_snapshot()
        cur = build_snapshot()
        features = parse_map()
        if prev is None:
            print("[aligner] nessuno snapshot precedente; scrivo il primo snapshot.")
            write_snapshot()
            prev = cur
        changes = diff_snapshots(prev, cur)
        actions = build_actions(changes, features)
        print_report(cur, changes, actions)
        # Persist the resolved actions alongside the snapshot for the agent.
        out = {
            "snapshot": cur,
            "changes": changes,
            "actions": [a.__dict__ for a in actions],
        }
        report_path = ROOT / "docs" / "frontend-alignment-report.json"
        report_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[aligner] report scritto: {report_path}")
        return 0
    print(f"comando sconosciuto: {cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
