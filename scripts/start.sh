#!/usr/bin/env bash
set -e

exec python main.py api --port ${PORT:-8000}
