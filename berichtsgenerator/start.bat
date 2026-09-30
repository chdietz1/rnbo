@echo off
REM Startet den Berichtsgenerator im lokalen Netzwerk (Port 8000).
cd /d "%~dp0"
if not exist .venv (
  py -3 -m venv .venv
  .venv\Scripts\pip install -r requirements.txt
)
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
