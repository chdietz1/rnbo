"""Textextraktion aus hochgeladenen Dateien, Aufteilung in Abschnitte und Indexierung."""
from __future__ import annotations

import copy
import difflib
import io
import re
import struct
import zipfile

from . import llm

SUPPORTED = (".pdf", ".docx", ".txt", ".md", ".rtf")

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200


class ExtractionError(ValueError):
    pass


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader

        try:
            reader = PdfReader(io.BytesIO(data))
            text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
            fields = _pdf_form_fields(reader)
            if fields:
                text += "\n\nAusgefüllte Formularfelder:\n" + "\n".join(fields)
        except Exception as e:  # pypdf wirft diverse Fehlertypen
            raise ExtractionError(f"PDF konnte nicht gelesen werden: {e}") from e
        if not text.strip():
            raise ExtractionError(
                "Im PDF wurde kein Text gefunden (vermutlich ein Scan). "
                "Bitte eine Textversion (Word/PDF mit Text) hochladen oder den Text einfügen."
            )
    elif name.endswith(".docx"):
        text = _docx_text(data)
    elif name.endswith(".rtf"):
        text = _strip_rtf(data.decode("latin-1", errors="replace"))
    elif name.endswith((".txt", ".md")):
        for enc in ("utf-8", "cp1252", "latin-1"):
            try:
                text = data.decode(enc)
                break
            except UnicodeDecodeError:
                continue
    else:
        raise ExtractionError(
            "Dateityp nicht unterstützt. Erlaubt: " + ", ".join(SUPPORTED)
        )
    return normalize(text)


# ---------------------------------------------------------------- Word (.docx)

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
CHECKED, UNCHECKED = "[x]", "[ ]"

# Häkchen als Symbol (Schriften Wingdings / Wingdings 2)
_SYMBOLS = {
    ("wingdings", "F0FE"): CHECKED, ("wingdings", "F0FD"): CHECKED, ("wingdings", "F078"): CHECKED,
    ("wingdings", "F0FC"): "✓", ("wingdings", "F0A8"): UNCHECKED, ("wingdings", "F06F"): UNCHECKED,
    ("wingdings", "F071"): UNCHECKED, ("wingdings 2", "F052"): CHECKED, ("wingdings 2", "F054"): CHECKED,
    ("wingdings 2", "F051"): CHECKED, ("wingdings 2", "F0A3"): UNCHECKED, ("wingdings 2", "F02A"): UNCHECKED,
}


def _docx_text(data: bytes) -> str:
    """Liest den Text in Dokumentreihenfolge, inkl. Tabellen, Textfeldern und Kontrollkästchen."""
    try:
        from lxml import etree

        with zipfile.ZipFile(io.BytesIO(data)) as z:
            root = etree.fromstring(z.read("word/document.xml"))
    except Exception as e:
        raise ExtractionError(f"Word-Datei konnte nicht gelesen werden: {e}") from e
    body = copy.deepcopy(root.find(f"{_W}body"))
    for fb in body.iter(_MC_FALLBACK):  # Textfelder sind doppelt gespeichert (neu + Fallback)
        fb.getparent().remove(fb)
    lines: list[str] = []
    _docx_block(body, lines)
    return "\n".join(lines)


def _docx_block(el, lines: list[str]) -> None:
    for child in el:
        if child.tag == f"{_W}p":
            lines.append(_docx_para(child))
        elif child.tag == f"{_W}tbl":
            for row in child.iter(f"{_W}tr"):
                if row.getparent() is not child:  # verschachtelte Tabellen landen in der Zelle
                    continue
                cells = []
                for tc in row.findall(f"{_W}tc"):
                    cell = " ".join(t for t in (_docx_para(p) for p in tc.iter(f"{_W}p")) if t.strip())
                    cells.append(cell.strip())
                if any(cells):
                    lines.append(" | ".join(cells))
            lines.append("")
        elif child.tag in (f"{_W}sdt", f"{_W}sdtContent", f"{_W}customXml"):
            _docx_block(child, lines)


def _docx_para(p) -> str:
    out: list[str] = []
    for el in p.iter():
        tag = el.tag
        if tag == f"{_W}t":
            out.append(el.text or "")
        elif tag == f"{_W}tab" and el.getparent().tag == f"{_W}r":
            out.append("\t")
        elif tag in (f"{_W}br", f"{_W}cr"):
            out.append("\n")
        elif tag == f"{_W}sym":
            font = (el.get(f"{_W}font") or "").lower()
            char = (el.get(f"{_W}char") or "").upper()
            if char and not char.startswith("F"):
                char = "F0" + char[-2:]
            out.append(_SYMBOLS.get((font, char), ""))
        elif tag == f"{_W}checkBox":  # alte Formular-Kontrollkästchen
            checked = el.find(f"{_W}checked")
            if checked is not None:
                is_on = checked.get(f"{_W}val", "1") not in ("0", "false")
            else:
                default = el.find(f"{_W}default")
                is_on = default is not None and default.get(f"{_W}val", "0") not in ("0", "false")
            out.append((CHECKED if is_on else UNCHECKED) + " ")
    return "".join(out)


# ---------------------------------------------------------------- PDF-Formulare


def _pdf_form_fields(reader) -> list[str]:
    try:
        fields = reader.get_fields() or {}
    except Exception:
        return []
    out = []
    for name, field in fields.items():
        value = field.get("/V")
        if value is None:
            continue
        value = str(value).strip()
        if field.get("/FT") == "/Btn":
            if value in ("/Off", "Off", ""):
                continue
            out.append(f"{CHECKED} {name}")
        elif value:
            out.append(f"{name}: {value}")
    return out


# ---------------------------------------------------------------- Abgleich mit leeren Vorlagen

TEMPLATE_TYPE = "Leere Vorlage (für Abgleich)"


def _norm_line(line: str) -> str:
    return re.sub(r"[\s_.…]+", " ", line).strip().lower()


def template_score(text: str, template: str) -> float:
    """Anteil der Vorlagenzeilen, die im Dokument vorkommen (0–1)."""
    t_lines = {_norm_line(l) for l in template.splitlines() if len(_norm_line(l)) > 3}
    if len(t_lines) < 5:
        return 0.0
    d_lines = {_norm_line(l) for l in text.splitlines()}
    return len(t_lines & d_lines) / len(t_lines)


def strip_template(text: str, template: str) -> str:
    """Behält nur, was gegenüber der leeren Vorlage neu ist, jeweils mit der vorangehenden
    Vorlagenzeile (meist die Überschrift bzw. Frage) als Kontext."""
    a = [l for l in template.splitlines() if l.strip()]
    b = [l for l in text.splitlines() if l.strip()]
    sm = difflib.SequenceMatcher(None, [_norm_line(x) for x in a], [_norm_line(x) for x in b], autojunk=False)
    out: list[str] = []
    context = None
    for tag, _i1, _i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            context = b[j2 - 1]
        elif tag in ("insert", "replace"):
            new = [l for l in b[j1:j2] if not l.strip().startswith(UNCHECKED)]
            if not new:
                continue
            if context:
                out.append("")
                out.append(context)
                context = None
            out.extend(new)
    return "\n".join(out).strip()


def apply_template(text: str, templates: list[dict], choice: str = "auto") -> tuple[str, dict | None]:
    """Gibt (reduzierter Text, verwendete Vorlage) zurück. choice: 'auto', 'none' oder eine Vorlagen-ID."""
    if choice == "none" or not templates:
        return text, None
    if choice == "auto":
        scored = sorted(((template_score(text, t["content_text"]), t) for t in templates), key=lambda x: -x[0])
        if not scored or scored[0][0] < 0.4:
            return text, None
        template = scored[0][1]
    else:
        template = next((t for t in templates if str(t["id"]) == str(choice)), None)
        if template is None:
            return text, None
    return strip_template(text, template["content_text"]), template


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00ad", "")
    # Kontrollkästchen als Zeichen vereinheitlichen
    text = re.sub(r"[☒☑■▣✅]", CHECKED, text)
    text = re.sub(r"[☐□▢]", UNCHECKED, text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _strip_rtf(rtf: str) -> str:
    rtf = re.sub(r"\\'([0-9a-fA-F]{2})", lambda m: bytes([int(m.group(1), 16)]).decode("cp1252", "replace"), rtf)
    rtf = re.sub(r"\\par[d]?", "\n", rtf)
    rtf = re.sub(r"\{\\\*[^{}]*\}", "", rtf)
    rtf = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", rtf)
    return rtf.replace("{", "").replace("}", "")


def chunk_text(text: str) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for p in paragraphs:
        while len(p) > CHUNK_SIZE:
            if current:
                chunks.append(current)
                current = ""
            cut = p.rfind(". ", 0, CHUNK_SIZE)
            cut = cut + 1 if cut > CHUNK_SIZE // 2 else CHUNK_SIZE
            chunks.append(p[:cut].strip())
            p = p[max(0, cut - CHUNK_OVERLAP):].strip()
        if len(current) + len(p) + 2 > CHUNK_SIZE and current:
            chunks.append(current)
            tail = current[-CHUNK_OVERLAP:]
            current = tail[tail.find(" ") + 1:] + "\n\n" + p if " " in tail else p
        else:
            current = f"{current}\n\n{p}" if current else p
    if current:
        chunks.append(current)
    return chunks


def pack_embedding(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def unpack_embedding(blob: bytes) -> list[float]:
    return list(struct.unpack(f"{len(blob) // 4}f", blob))


def index_document(conn, document_id: int, text: str) -> None:
    conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
    chunks = chunk_text(text)
    embeddings = llm.embed(chunks) if chunks else None
    for i, chunk in enumerate(chunks):
        emb = pack_embedding(embeddings[i]) if embeddings and i < len(embeddings) else None
        conn.execute(
            "INSERT INTO chunks (document_id, idx, text, embedding) VALUES (?, ?, ?, ?)",
            (document_id, i, chunk, emb),
        )
