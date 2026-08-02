#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$REPO_ROOT/frontend"
STATIC_DIR="$REPO_ROOT/bike_analyzer/backend/static"
DIST_DIR="$FRONTEND_DIR/dist"

SKIP_BUILD="${SKIP_BUILD:-0}"

echo "[copy_front_to_static] repo root: $REPO_ROOT"

if [ "$SKIP_BUILD" = "0" ]; then
    echo "[copy_front_to_static] building frontend (npm run build)..."
    (cd "$FRONTEND_DIR" && npm run build)
fi

if [ ! -d "$DIST_DIR" ]; then
    echo "[copy_front_to_static] ERROR: $DIST_DIR does not exist" >&2
    echo "[copy_front_to_static] run with SKIP_BUILD=1 after building manually, or let the script build first." >&2
    exit 1
fi

mkdir -p "$STATIC_DIR"
echo "[copy_front_to_static] copying $DIST_DIR/* -> $STATIC_DIR/"
cp -a "$DIST_DIR/." "$STATIC_DIR/"
echo "[copy_front_to_static] done. index.html: $([ -f "$STATIC_DIR/index.html" ] && echo OK || echo MISSING)"
