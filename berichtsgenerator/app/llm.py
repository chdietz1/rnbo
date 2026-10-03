"""Anbindung an das lokale Sprachmodell (Ollama). Es werden keine Daten ins Internet gesendet."""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from . import config


class LLMError(RuntimeError):
    pass


async def chat_stream(messages: list[dict]) -> AsyncIterator[str]:
    if config.LLM_BACKEND == "mock":
        async for piece in _mock_stream(messages):
            yield piece
        return

    payload = {
        "model": config.MODEL,
        "messages": messages,
        "stream": True,
        "options": {"num_ctx": config.NUM_CTX, "temperature": config.TEMPERATURE},
    }
    try:
        async with httpx.AsyncClient(timeout=config.LLM_TIMEOUT) as client:
            async with client.stream("POST", f"{config.OLLAMA_URL}/api/chat", json=payload) as r:
                if r.status_code != 200:
                    body = (await r.aread()).decode(errors="replace")
                    raise LLMError(f"Ollama antwortet mit Status {r.status_code}: {body[:300]}")
                async for line in r.aiter_lines():
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    if data.get("error"):
                        raise LLMError(data["error"])
                    piece = data.get("message", {}).get("content", "")
                    if piece:
                        yield piece
                    if data.get("done"):
                        break
    except httpx.HTTPError as e:
        raise LLMError(
            f"Keine Verbindung zum lokalen Sprachmodell ({config.OLLAMA_URL}). "
            f"Läuft Ollama? Details: {e}"
        ) from e


async def chat_complete(messages: list[dict]) -> str:
    """Wie chat_stream, liefert aber die ganze Antwort auf einmal."""
    parts = []
    async for piece in chat_stream(messages):
        parts.append(piece)
    return "".join(parts)


def embed(texts: list[str]) -> list[list[float]] | None:
    """Liefert Embeddings oder None, wenn kein Embedding-Modell verfügbar ist."""
    if config.LLM_BACKEND == "mock" or not config.EMBED_MODEL or not texts:
        return None
    try:
        r = httpx.post(
            f"{config.OLLAMA_URL}/api/embed",
            json={"model": config.EMBED_MODEL, "input": texts},
            timeout=300,
        )
        r.raise_for_status()
        return r.json().get("embeddings")
    except (httpx.HTTPError, ValueError):
        return None


def status() -> dict:
    if config.LLM_BACKEND == "mock":
        return {"ok": True, "backend": "mock", "models": [], "model": "mock", "model_ok": True}
    try:
        r = httpx.get(f"{config.OLLAMA_URL}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]

        def has(name: str) -> bool:
            return any(m == name or m.split(":")[0] == name or m == f"{name}:latest" for m in models)

        return {
            "ok": True,
            "backend": "ollama",
            "models": models,
            "model": config.MODEL,
            "model_ok": has(config.MODEL),
            "embed_model": config.EMBED_MODEL,
            "embed_ok": bool(config.EMBED_MODEL) and has(config.EMBED_MODEL),
        }
    except (httpx.HTTPError, ValueError) as e:
        return {"ok": False, "backend": "ollama", "error": str(e), "model": config.MODEL}


async def _mock_stream(messages: list[dict]) -> AsyncIterator[str]:
    """Platzhalter-Ausgabe für Tests und Demos ohne installiertes Modell."""
    user = messages[-1]["content"]
    if "AUSGANGSLAGE:" in user:  # Befähigungsschwerpunkte: verlangtes Format nachbilden
        notes = user.rsplit("(wichtigste und aktuellste Quelle) ===", 1)[-1].split("Schreibe jetzt")[0].strip()
        text = (
            f"AUSGANGSLAGE:\nTestausgabe (mock). Stichworte: {notes.replace(chr(10), ' ')}\n"
            + ("LP21:\nPersonale Kompetenzen – Selbstständigkeit\n" if "LP21:" in user else "")
            + "WAS:\nTestsatz zum Bezug.\nWO:\nTestsatz zum Kontext.\n"
        )
        for i in range(0, len(text), 20):
            yield text[i : i + 20]
        return
    text = (
        "## Hinweis\n"
        "Dies ist eine Testausgabe (BG_LLM_BACKEND=mock). Es wurde kein Sprachmodell verwendet.\n\n"
        "## Übermittelter Kontext\n"
        f"- Länge des Auftrags: {len(user)} Zeichen\n"
        f"- Enthält frühere Unterlagen: {'ja' if 'FRÜHERE UNTERLAGEN' in user else 'nein'}\n"
        f"- Enthält Grundlagen: {'ja' if 'KANTONALE GRUNDLAGEN' in user else 'nein'}\n"
    )
    for i in range(0, len(text), 20):
        yield text[i : i + 20]
