"""Passwort-Hashing (scrypt, Standardbibliothek), Sitzungen, CSRF-Schutz und Rechte."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import defaultdict

from fastapi import HTTPException, Request

from . import db

_N, _R, _P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return f"scrypt${salt.hex()}${h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, hash_hex = stored.split("$")
    except ValueError:
        return False
    h = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=_N, r=_R, p=_P)
    return hmac.compare_digest(h.hex(), hash_hex)


def validate_new_password(password: str) -> str | None:
    if len(password) < 10:
        return "Das Passwort muss mindestens 10 Zeichen lang sein."
    return None


# Einfacher Schutz gegen Passwort-Raten: max. 8 Fehlversuche pro 15 Minuten
_failed: dict[str, list[float]] = defaultdict(list)
WINDOW, MAX_FAILS = 900, 8


def too_many_attempts(key: str) -> bool:
    now = time.time()
    _failed[key] = [t for t in _failed[key] if now - t < WINDOW]
    return len(_failed[key]) >= MAX_FAILS


def register_failure(key: str) -> None:
    _failed[key].append(time.time())


def clear_failures(key: str) -> None:
    _failed.pop(key, None)


def csrf_token(request: Request) -> str:
    token = request.session.get("csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf"] = token
    return token


def check_csrf(request: Request, token: str | None) -> None:
    expected = request.session.get("csrf")
    if not expected or not token or not hmac.compare_digest(expected, token):
        raise HTTPException(status_code=403, detail="Ungültiges Formular-Token. Bitte Seite neu laden.")


def current_user(request: Request):
    uid = request.session.get("uid")
    if not uid:
        return None
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ? AND active = 1", (uid,)).fetchone()
    return dict(row) if row else None


class LoginRequired(Exception):
    pass


def require_user(request: Request) -> dict:
    user = current_user(request)
    if not user:
        raise LoginRequired()
    return user


def require_admin(request: Request) -> dict:
    user = require_user(request)
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Nur für Administratorinnen/Administratoren.")
    return user


def can_access_student(conn, user: dict, student_id: int) -> bool:
    if user["is_admin"]:
        return conn.execute("SELECT 1 FROM students WHERE id = ?", (student_id,)).fetchone() is not None
    return (
        conn.execute(
            "SELECT 1 FROM student_users WHERE student_id = ? AND user_id = ?",
            (student_id, user["id"]),
        ).fetchone()
        is not None
    )


def get_student_or_403(conn, user: dict, student_id: int) -> dict:
    if not can_access_student(conn, user, student_id):
        raise HTTPException(status_code=404, detail="Nicht gefunden oder keine Berechtigung.")
    return dict(conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone())
