"""Kommandozeilenwerkzeuge.

    python -m app.cli create-user <benutzername> "<Name>" [--admin]
    python -m app.cli reset-password <benutzername>
    python -m app.cli backup [zielordner]
    python -m app.cli demo      (Testkonto und erfundene Beispieldaten anlegen)
"""
from __future__ import annotations

import argparse
import getpass
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from . import auth, config, db, documents

DEMO_USER, DEMO_PASSWORD = "demo", "demo-passwort"

# Erfundene Beispieldaten zum Ausprobieren
DEMO_DOCS = [
    ("Beurteilungsbericht 2. Semester 2024/25", "Beurteilungsbericht", "2025-06-27",
     "Lina liest vertraute Wörter mit Silbenbögen. Längere Wörter zerlegt sie mit Unterstützung in Silben. "
     "Im Zahlenraum bis 20 rechnet sie sicher, bis 100 mit Material. Sie arbeitet etwa 5 bis 10 Minuten "
     "selbstständig, danach braucht sie eine Rückmeldung der Lehrperson. Bei Konflikten in der Pause zieht "
     "sie sich oft zurück. Lina zeigt grosse Freude an Zahlen und erklärt gern."),
    ("Protokoll Standortgespräch", "Protokoll Standortgespräch", "2025-06-19",
     "Teilnehmende: Erziehungsberechtigte, Klassenlehrperson, Schulische Heilpädagogin, Logopädin.\n\n"
     "Vereinbarte Förderziele 2025/26:\n1. Lina liest kurze Texte und beantwortet Fragen dazu.\n"
     "2. Lina addiert und subtrahiert im Zahlenraum bis 100.\n"
     "3. Lina arbeitet 15 Minuten selbstständig mit einem visualisierten Arbeitsplan."),
    ("Förderplan 2025/26", "Förderplan", "2025-09-01",
     "Massnahmen: Silbenlesen mit farbigen Silbenbögen, täglich 10 Minuten Lesetraining. Hunderterfeld und "
     "Rechenrahmen. Arbeitsplan mit Bildkarten und Timer. Feste Rollen in Partnerarbeiten."),
]


def _ask_password() -> str:
    while True:
        pw = getpass.getpass("Passwort: ")
        error = auth.validate_new_password(pw)
        if error:
            print(error)
        elif pw != getpass.getpass("Wiederholen: "):
            print("Die Passwörter stimmen nicht überein.")
        else:
            return pw


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("create-user", help="Benutzer erstellen")
    p.add_argument("username")
    p.add_argument("display_name")
    p.add_argument("--admin", action="store_true")
    p = sub.add_parser("reset-password", help="Passwort zurücksetzen")
    p.add_argument("username")
    sub.add_parser("demo", help="Testkonto und erfundene Beispieldaten anlegen")
    p = sub.add_parser("backup", help="Konsistente Sicherung der Datenbank erstellen")
    p.add_argument("target", nargs="?", default=str(config.DATA_DIR / "backups"))
    args = parser.parse_args(argv)

    db.init_db()
    if args.cmd == "create-user":
        pw = _ask_password()
        with db.get_conn() as conn:
            conn.execute(
                "INSERT INTO users (username, display_name, pw_hash, is_admin, created_at) VALUES (?, ?, ?, ?, ?)",
                (args.username, args.display_name, auth.hash_password(pw), int(args.admin), db.now()),
            )
        print(f"Benutzer «{args.username}» erstellt.")
    elif args.cmd == "reset-password":
        pw = _ask_password()
        with db.get_conn() as conn:
            cur = conn.execute("UPDATE users SET pw_hash = ?, active = 1 WHERE username = ?",
                               (auth.hash_password(pw), args.username))
        if not cur.rowcount:
            print("Benutzer nicht gefunden.")
            return 1
        print("Passwort gesetzt.")
    elif args.cmd == "demo":
        with db.get_conn() as conn:
            user = conn.execute("SELECT * FROM users WHERE username = ?", (DEMO_USER,)).fetchone()
            if user:
                print("Demo-Daten sind bereits vorhanden.")
                return 0
            if conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
                print("Es gibt bereits Benutzerkonten. Es werden keine Demo-Daten angelegt.")
                return 0
            cur = conn.execute(
                "INSERT INTO users (username, display_name, pw_hash, is_admin, created_at) VALUES (?, ?, ?, 1, ?)",
                (DEMO_USER, "Demo Lehrperson", auth.hash_password(DEMO_PASSWORD), db.now()),
            )
            uid = cur.lastrowid
            cur = conn.execute(
                "INSERT INTO students (first_name, last_name, birth_year, class_name, notes, created_at) "
                "VALUES ('Lina', 'Beispiel', '2015', 'Mittelstufe, Klasse M2', 'Erfundenes Beispiel', ?)",
                (db.now(),),
            )
            sid = cur.lastrowid
            conn.execute("INSERT INTO student_users (student_id, user_id) VALUES (?, ?)", (sid, uid))
            for title, doc_type, date, text in DEMO_DOCS:
                cur = conn.execute(
                    "INSERT INTO documents (student_id, title, doc_type, doc_date, content_text, uploaded_by, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (sid, title, doc_type, date, text, uid, db.now()),
                )
                documents.index_document(conn, cur.lastrowid, text)
        print(f"Demo-Daten angelegt. Anmelden mit Benutzername «{DEMO_USER}» und Passwort «{DEMO_PASSWORD}».")
    elif args.cmd == "backup":
        target = Path(args.target)
        target.mkdir(parents=True, exist_ok=True)
        dest = target / f"berichte-{datetime.now():%Y%m%d-%H%M%S}.sqlite3"
        src = sqlite3.connect(config.DB_PATH)
        with sqlite3.connect(dest) as out:
            src.backup(out)
        src.close()
        print(f"Sicherung erstellt: {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
