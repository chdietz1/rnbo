#!/bin/bash
# Berichtsgenerator auf dem Mac starten (Doppelklick oder: bash start-mac.command)
cd "$(dirname "$0")" || exit 1

pause() { echo; read -r -p "Zum Schliessen Enter drücken …"; }

echo "=== Berichtsgenerator ==="

# 1. Python prüfen (mind. 3.9)
PY=$(command -v python3)
if [ -z "$PY" ] || ! "$PY" -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
  echo "Python 3 fehlt. Bitte von https://www.python.org/downloads/ installieren und erneut starten."
  open "https://www.python.org/downloads/"
  pause; exit 1
fi

# 2. Einstellungen für einen Mac mit 16 GB anlegen (nur beim ersten Mal)
if [ ! -f .env ]; then
  cat > .env <<'ENV'
BG_SCHOOL_NAME=Testschule
BG_MODEL=gemma3:12b
BG_NUM_CTX=8192
# leer = Stichwortsuche (spart Arbeitsspeicher)
BG_EMBED_MODEL=
ENV
fi
MODEL=$(grep -E '^BG_MODEL=' .env | cut -d= -f2)
MODEL=${MODEL:-gemma3:12b}

# 3. Ollama starten, falls es nicht läuft
if ! curl -s http://127.0.0.1:11434/api/tags >/dev/null; then
  echo "Starte Ollama …"
  open -a Ollama 2>/dev/null
  for _ in $(seq 1 30); do
    curl -s http://127.0.0.1:11434/api/tags >/dev/null && break
    sleep 1
  done
fi
if ! curl -s http://127.0.0.1:11434/api/tags >/dev/null; then
  echo "Ollama läuft nicht. Bitte die Ollama-App öffnen und erneut starten."
  pause; exit 1
fi

# 4. Modell herunterladen, falls es fehlt (einmalig, braucht Internet)
if ! curl -s http://127.0.0.1:11434/api/tags | grep -q "\"$MODEL\""; then
  echo "Lade Sprachmodell $MODEL herunter (einmalig, mehrere GB) …"
  if command -v ollama >/dev/null; then
    ollama pull "$MODEL" || { pause; exit 1; }
  else
    curl -s http://127.0.0.1:11434/api/pull -d "{\"model\":\"$MODEL\",\"stream\":false}" || { pause; exit 1; }
  fi
fi

# 5. Python-Umgebung einrichten (einmalig)
if [ ! -d .venv ]; then
  echo "Richte Python-Umgebung ein (einmalig) …"
  "$PY" -m venv .venv && .venv/bin/pip install -q --upgrade pip && .venv/bin/pip install -q -r requirements.txt \
    || { echo "Installation fehlgeschlagen."; rm -rf .venv; pause; exit 1; }
fi

# 6. Beispieldaten beim ersten Start
if [ ! -f data/berichte.sqlite3 ]; then
  .venv/bin/python -m app.cli demo
fi

echo
echo "Läuft auf http://localhost:8000"
echo "Anmelden: Benutzername «demo», Passwort «demo-passwort»"
echo "Zum Beenden dieses Fenster schliessen oder Ctrl+C drücken."
echo
(sleep 3; open "http://localhost:8000") &
# Nur auf diesem Mac erreichbar. Für das Schulnetz 127.0.0.1 durch 0.0.0.0 ersetzen.
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
