"""Import von Schülerlisten (Excel .xlsx oder CSV) zum Anlegen mehrerer Dossiers."""
from __future__ import annotations

import csv
import io
import re

# Erkannte Spaltenüberschriften (klein geschrieben, ohne Leer- und Sonderzeichen)
COLUMNS = {
    "first_name": ("vorname", "firstname"),
    "last_name": ("nachname", "name", "familienname", "lastname"),
    "birth_year": ("jahrgang", "geburtsjahr", "jg"),
    "class_name": ("klasse", "stufe", "klassestufe", "gruppe"),
    "teachers": ("lehrpersonen", "lehrperson", "zugriff", "benutzer", "benutzername"),
}

TEMPLATE_CSV = "Vorname;Nachname;Jahrgang;Klasse;Lehrpersonen\nLina;Beispiel;2015;Mittelstufe M2;skeller, mbrunner\n"


class ImportError_(ValueError):
    pass


def _key(header: str) -> str:
    return re.sub(r"[^a-zäöü]", "", str(header or "").lower())


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():  # Excel liefert Jahrgänge oft als 2015.0
        value = int(value)
    return str(value).strip()


def _read_rows(filename: str, data: bytes) -> list[list[str]]:
    name = filename.lower()
    if name.endswith(".xlsx"):
        try:
            import openpyxl
        except ImportError as e:
            raise ImportError_("Für Excel-Dateien fehlt das Paket «openpyxl». Bitte als CSV speichern.") from e
        try:
            wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        except Exception as e:
            raise ImportError_(f"Excel-Datei konnte nicht gelesen werden: {e}") from e
        ws = wb.worksheets[0]
        return [[_cell(c) for c in row] for row in ws.iter_rows(values_only=True)]
    if name.endswith((".csv", ".txt")):
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                text = data.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        first = text.splitlines()[0] if text.strip() else ""
        delimiter = ";" if first.count(";") >= first.count(",") else ","
        if "\t" in first and first.count("\t") > first.count(delimiter):
            delimiter = "\t"
        return [[_cell(c) for c in row] for row in csv.reader(io.StringIO(text), delimiter=delimiter)]
    raise ImportError_("Bitte eine Excel-Datei (.xlsx) oder CSV-Datei hochladen.")


def parse_students(filename: str, data: bytes) -> tuple[list[dict], list[str]]:
    """Liefert (gültige Zeilen, Fehlermeldungen)."""
    rows = [r for r in _read_rows(filename, data) if any(r)]
    if not rows:
        raise ImportError_("Die Datei ist leer.")
    header = [_key(h) for h in rows[0]]
    index = {}
    for field, names in COLUMNS.items():
        for i, h in enumerate(header):
            if h in names:
                index[field] = i
                break
    if "first_name" not in index or "last_name" not in index:
        raise ImportError_(
            "In der ersten Zeile braucht es mindestens die Spalten «Vorname» und «Nachname»."
        )

    students, errors = [], []
    for line_no, row in enumerate(rows[1:], start=2):
        get = lambda f: row[index[f]].strip() if f in index and index[f] < len(row) else ""
        entry = {f: get(f) for f in COLUMNS}
        if not entry["first_name"] or not entry["last_name"]:
            errors.append(f"Zeile {line_no}: Vor- oder Nachname fehlt, übersprungen.")
            continue
        entry["teachers"] = [t.strip() for t in re.split(r"[,;/]", entry["teachers"]) if t.strip()]
        entry["line"] = line_no
        students.append(entry)
    return students, errors


def import_students(conn, students: list[dict], importer: dict) -> dict:
    users = {r["username"].lower(): r["id"] for r in conn.execute("SELECT id, username FROM users WHERE active = 1")}
    created, skipped, messages = 0, 0, []
    unknown: set[str] = set()
    from . import db

    for s in students:
        exists = conn.execute(
            "SELECT id FROM students WHERE lower(first_name) = lower(?) AND lower(last_name) = lower(?) "
            "AND COALESCE(birth_year, '') = ?",
            (s["first_name"], s["last_name"], s["birth_year"]),
        ).fetchone()
        if exists:
            skipped += 1
            messages.append(f"Zeile {s['line']}: {s['first_name']} {s['last_name']} existiert bereits, übersprungen.")
            continue
        cur = conn.execute(
            "INSERT INTO students (first_name, last_name, birth_year, class_name, notes, created_at) VALUES (?, ?, ?, ?, '', ?)",
            (s["first_name"], s["last_name"], s["birth_year"], s["class_name"], db.now()),
        )
        for t in s["teachers"]:
            uid = users.get(t.lower())
            if uid:
                conn.execute("INSERT OR IGNORE INTO student_users (student_id, user_id) VALUES (?, ?)", (cur.lastrowid, uid))
            else:
                unknown.add(t)
        created += 1
    if unknown:
        messages.append(
            "Unbekannte Benutzernamen (Zugriff nicht erteilt): " + ", ".join(sorted(unknown))
            + ". Benutzer zuerst erfassen und Zugriff im Dossier freigeben."
        )
    db.audit(conn, importer, "schueler_importiert", f"neu={created} uebersprungen={skipped}")
    return {"created": created, "skipped": skipped, "messages": messages}
