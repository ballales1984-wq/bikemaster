"""Vercel serverless entrypoint for BikeMaster Hub.

Exposes the hub FastAPI app as a Vercel Python serverless function.
All /api/* requests are routed here by Vercel's runtime.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from bike_analyzer.backend.hub.main import create_hub_app  # noqa: E402

app = create_hub_app()
