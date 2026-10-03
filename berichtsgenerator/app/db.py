"""SQLite-Datenbank: Schema und kleine Hilfsfunktionen."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    display_name TEXT NOT NULL,
    pw_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    birth_year TEXT,
    class_name TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);

-- Welche Lehrpersonen dürfen welche Schülerinnen/Schüler sehen
CREATE TABLE IF NOT EXISTS student_users (
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (student_id, user_id)
);

-- student_id NULL = Dokument der Wissensbasis (Vorgaben, Leitfäden, Lehrplan ...)
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    doc_date TEXT,
    filename TEXT,
    content_text TEXT NOT NULL,
    uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding BLOB
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);

CREATE TABLE IF NOT EXISTS report_types (
    id INTEGER PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    instructions TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    sort INTEGER NOT NULL DEFAULT 100
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    report_type_id INTEGER REFERENCES report_types(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    period TEXT,
    observations TEXT,
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'entwurf',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Gespeicherte Anweisungen («Skills») von Lehrpersonen
CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY,
    owner_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    text TEXT NOT NULL,
    shared INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,
    user_id INTEGER,
    username TEXT,
    action TEXT NOT NULL,
    detail TEXT
);
"""


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def get_conn():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    from .prompts import DEFAULT_REPORT_TYPES

    with get_conn() as conn:
        conn.executescript(SCHEMA)
        # Spalten, die in späteren Versionen dazugekommen sind
        existing = {r["name"] for r in conn.execute("PRAGMA table_info(documents)")}
        if "full_text" not in existing:  # Originaltext vor dem Abgleich mit einer Vorlage
            conn.execute("ALTER TABLE documents ADD COLUMN full_text TEXT")
        if "template_id" not in existing:
            conn.execute("ALTER TABLE documents ADD COLUMN template_id INTEGER")
        for i, rt in enumerate(DEFAULT_REPORT_TYPES):
            conn.execute(
                "INSERT OR IGNORE INTO report_types (key, name, description, instructions, sort) "
                "VALUES (?, ?, ?, ?, ?)",
                (rt["key"], rt["name"], rt["description"], rt["instructions"], (i + 1) * 10),
            )


def audit(conn: sqlite3.Connection, user, action: str, detail: str = "") -> None:
    conn.execute(
        "INSERT INTO audit (ts, user_id, username, action, detail) VALUES (?, ?, ?, ?, ?)",
        (now(), user["id"] if user else None, user["username"] if user else None, action, detail),
    )
