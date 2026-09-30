#!/usr/bin/env bash
# Startet den Berichtsgenerator im lokalen Netzwerk (Port 8000).
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
exec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "${BG_PORT:-8000}"
