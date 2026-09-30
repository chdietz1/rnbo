"""Auswahl der relevanten Unterlagen für das Sprachmodell (einfaches RAG).

- Unterlagen zum Kind: passen sie ins Budget, werden sie vollständig (neueste
  zuerst) übergeben; sonst die relevantesten Abschnitte.
- Wissensbasis: die relevantesten Abschnitte (Embeddings, sonst Stichwortsuche).
"""
import math
import re
from collections import Counter

from . import config, llm
from .documents import unpack_embedding

STOPWORDS = set(
    """aber alle allem allen aller alles als also am an ander andere anderem anderen anderer
    anderes auch auf aus bei bin bis bist da damit dann das dass dein deine dem den der des
    dessen die dies diese diesem diesen dieser dieses doch dort du durch ein eine einem einen
    einer eines er es etwas euch euer für gegen hat hatte hier hin hinter ich ihm ihn ihnen
    ihr ihre im in indem ins ist jede jedem jeden jeder jedes jetzt kann kein keine können
    machen man manche mehr mein mit muss nach nicht nichts noch nun nur ob oder ohne sehr sein
    seine sich sie sind so solche soll sondern sonst über um und uns unser unter viel vom von
    vor während war waren was weg weil weiter welche wenn werden wie wieder will wir wird wo
    wurde zu zum zur zwar zwischen sowie bzw z b""".split()
)


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zäöüàéèç]{3,}", text.lower())
    out = []
    for t in tokens:
        if t in STOPWORDS:
            continue
        for suffix in ("ungen", "ung", "en", "er", "es", "e", "n", "s"):
            if len(t) > 5 and t.endswith(suffix):
                t = t[: -len(suffix)]
                break
        out.append(t)
    return out


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def rank_chunks(query: str, chunks: list[dict]) -> list[tuple[float, dict]]:
    if not chunks:
        return []
    q_emb = None
    if any(c["embedding"] for c in chunks):
        res = llm.embed([query])
        q_emb = res[0] if res else None

    # BM25-ähnliche Stichwortbewertung
    q_tokens = set(tokenize(query))
    docs_tokens = [Counter(tokenize(c["text"])) for c in chunks]
    n = len(chunks)
    df = Counter()
    for toks in docs_tokens:
        df.update(set(toks))
    avg_len = sum(sum(t.values()) for t in docs_tokens) / n or 1

    scored = []
    for c, toks in zip(chunks, docs_tokens):
        length = sum(toks.values()) or 1
        kw = 0.0
        for t in q_tokens:
            if t in toks:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                tf = toks[t]
                kw += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * length / avg_len))
        score = kw
        if q_emb is not None and c["embedding"]:
            score = _cosine(q_emb, unpack_embedding(c["embedding"])) * 10 + kw * 0.3
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def budgets() -> tuple[int, int]:
    """Zeichenbudget für (Unterlagen zum Kind, Wissensbasis)."""
    usable_tokens = max(config.NUM_CTX - 3500, 1500)  # Reserve für Prompt + Antwort
    chars = usable_tokens * 3
    return int(chars * 0.7), int(chars * 0.3)


def _doc_header(doc) -> str:
    date = f", {doc['doc_date']}" if doc["doc_date"] else ""
    return f"--- {doc['doc_type']}: {doc['title']}{date} ---"


def build_student_context(conn, document_ids: list[int], query: str, budget: int) -> str:
    if not document_ids:
        return ""
    marks = ",".join("?" * len(document_ids))
    docs = conn.execute(
        f"SELECT * FROM documents WHERE id IN ({marks}) "
        "ORDER BY COALESCE(doc_date, created_at) DESC",
        document_ids,
    ).fetchall()
    total = sum(len(d["content_text"]) + 80 for d in docs)
    if total <= budget:
        return "\n\n".join(f"{_doc_header(d)}\n{d['content_text']}" for d in docs)

    chunks = [
        dict(r)
        for r in conn.execute(
            f"SELECT * FROM chunks WHERE document_id IN ({marks})", document_ids
        ).fetchall()
    ]
    selected = _select_within_budget(rank_chunks(query, chunks), budget)
    out = []
    for d in docs:  # neueste Dokumente zuerst, Abschnitte in Originalreihenfolge
        parts = sorted((c for c in selected if c["document_id"] == d["id"]), key=lambda c: c["idx"])
        if parts:
            out.append(_doc_header(d) + " (Auszüge)\n" + "\n[…]\n".join(c["text"] for c in parts))
    return "\n\n".join(out)


def build_kb_context(conn, query: str, budget: int) -> str:
    rows = conn.execute(
        "SELECT c.*, d.title, d.doc_type FROM chunks c JOIN documents d ON d.id = c.document_id "
        "WHERE d.student_id IS NULL"
    ).fetchall()
    chunks = [dict(r) for r in rows]
    ranked = [(s, c) for s, c in rank_chunks(query, chunks) if s > 0]
    selected = _select_within_budget(ranked, budget)
    return "\n\n".join(f"--- {c['title']} ---\n{c['text']}" for c in selected)


def _select_within_budget(ranked: list[tuple[float, dict]], budget: int) -> list[dict]:
    selected, used = [], 0
    for _, c in ranked:
        size = len(c["text"]) + 40
        if used + size > budget:
            continue
        selected.append(c)
        used += size
    return selected
