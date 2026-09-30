"""Konfiguration über Umgebungsvariablen (siehe .env.example)."""
import os
import secrets
from pathlib import Path


def _load_dotenv() -> None:
    """Minimaler .env-Loader, damit keine zusätzliche Abhängigkeit nötig ist."""
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("BG_DATA_DIR", BASE_DIR / "data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "berichte.sqlite3"

# LLM-Backend: "ollama" (Standard, lokal) oder "mock" (nur für Tests/Demo ohne Modell)
LLM_BACKEND = os.environ.get("BG_LLM_BACKEND", "ollama")
OLLAMA_URL = os.environ.get("BG_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
MODEL = os.environ.get("BG_MODEL", "gemma3:12b")
# Leer lassen, um nur die Stichwortsuche zu verwenden
EMBED_MODEL = os.environ.get("BG_EMBED_MODEL", "bge-m3")
NUM_CTX = int(os.environ.get("BG_NUM_CTX", "16384"))
TEMPERATURE = float(os.environ.get("BG_TEMPERATURE", "0.4"))
LLM_TIMEOUT = float(os.environ.get("BG_LLM_TIMEOUT", "900"))

SESSION_MAX_AGE = int(os.environ.get("BG_SESSION_HOURS", "8")) * 3600
# Auf "1" setzen, wenn die Anwendung hinter HTTPS (z.B. Reverse Proxy) läuft
HTTPS_ONLY = os.environ.get("BG_HTTPS_ONLY", "0") == "1"
MAX_UPLOAD_MB = int(os.environ.get("BG_MAX_UPLOAD_MB", "25"))
SCHOOL_NAME = os.environ.get("BG_SCHOOL_NAME", "Schule")


def _secret_key() -> str:
    key = os.environ.get("BG_SECRET_KEY")
    if key:
        return key
    key_file = DATA_DIR / ".secret_key"
    if key_file.exists():
        return key_file.read_text().strip()
    key = secrets.token_urlsafe(48)
    key_file.write_text(key)
    try:
        key_file.chmod(0o600)
    except OSError:
        pass
    return key


SECRET_KEY = _secret_key()
