"""Kommandozeilenwerkzeuge.

    python -m app.cli create-user <benutzername> "<Name>" [--admin]
    python -m app.cli reset-password <benutzername>
    python -m app.cli backup [zielordner]
"""
import argparse
import getpass
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from . import auth, config, db


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
