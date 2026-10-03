"""Befähigungsschwerpunkte planen: Die Lehrperson wählt Bereiche, Unterpunkte und
Unter-Unter-Punkte; die App setzt Kästchen, Kommentar, Titel und Aufzählungen wörtlich
ein. Das Sprachmodell schreibt pro Bereich nur Ausgangslage, WAS und WO."""
from __future__ import annotations

import re

from .prompts import SYSTEM_PROMPT

# Befähigungsbereiche und deren Inhalte (Anwendungsbereiche Lehrplan 21, Originalwortlaut)
CATALOGUE = [
    {"num": "I", "name": "Sich selbst sein und werden", "unterpunkte": [
        {"title": "Selbstempfinden – sich selbst wahrnehmen", "items": [
            "Sich als ein «unveränderliches Ganzes» wahrzunehmen",
            "Den Körper als ein zusammengehörendes Ganzes erleben",
            "Spannungszustände erfahren und bewältigen"]},
        {"title": "Urheberschaft – sich als wirksam erleben", "items": [
            "Sich als wirksam erleben",
            "Ein positives Selbstkonzept entwickeln",
            "Vertrauen in die eigenen Stärken zeigen"]},
        {"title": "Selbstausdruck – sich ausdrücken und einbringen", "items": [
            "Fähigkeit zum Selbstausdruck entwickeln",
            "Eigene Bedürfnisse und Wünsche mitteilen und sich dabei aktiv einbringen",
            "Ein überdauerndes Gefühl des Vertrauens und der Vorhersehbarkeiten erfahren"]},
    ]},
    {"num": "II", "name": "Sich und andere anerkennen", "unterpunkte": [
        {"title": "Integrität wahren – eigene und fremde Grenzen akzeptieren", "items": [
            "Die eigenen Unversehrtheiten schützen und bewahren, in Übereinstimmung mit sich sein",
            "Die Grenzen und Unversehrtheit des Gegenübers wahren",
            "Die eigenen Unverletzlichkeiten erfahren in Bezug auf den Körper sowie Gefühle"]},
        {"title": "Würdigung eigener Rechte und die des anderen – sich und andere respektieren", "items": [
            "Die eigenen Rechte erfahren und achten",
            "Die Rechte des anderen achten und schützen",
            "Dies in «Wort und Tat» ausdrücken"]},
        {"title": "Wertschätzung – Wertschätzung erleben und zeigen", "items": [
            "Achtung, Anerkennung und Respekt gegenüber Eigenschaften, Leistungen und dem Sein anderer zeigen",
            "Achtung, Anerkennung und Respekt gegenüber Eigenschaften, Leistungen und dem Sein erfahren",
            "Ein überdauerndes Gefühl des Vertrauens und der Vorhersehbarkeit erfahren"]},
    ]},
    {"num": "III", "name": "Sich austauschen und dazugehören", "unterpunkte": [
        {"title": "Vertrauen – sichere Bindung aufbauen", "items": [
            "Vertrauen zu anderen Menschen und zu Tieren fassen",
            "Nähe und Distanz zu anderen Menschen und Lebewesen regulieren, sowie Anwesenheit und Abwesenheit ertragen",
            "Stabilität und Sicherheit in Beziehungen erfahren"]},
        {"title": "Bindung – sich anderen zuwenden", "items": [
            "Bindung zu anderen Menschen und Tieren eingehen",
            "Sich Menschen und Tieren zuwenden",
            "Ein Gefühl von Zugehörigkeit zu Gruppen entwickeln"]},
        {"title": "Dialog – sich mit anderen austauschen", "items": [
            "Dialog als wechselseitiger Austausch erfahren, daran teilnehmen und sich mit passenden Antworten einbringen",
            "Erfahren, dass das eigene Handeln und Erfahrungen beim Gegenüber auf Anklang treffen, gesehen werden",
            "Den anderen wahrnehmen und diesem «Ich-sehe-Dich» Ausdruck geben"]},
    ]},
    {"num": "IV", "name": "Mitbestimmen und gestalten", "unterpunkte": [
        {"title": "Kooperation – mit anderen kooperieren", "items": [
            "Mit anderen Menschen zusammenarbeiten",
            "Sich auf gemeinsame Tätigkeiten in verschiedenen Lebenswelten einlassen",
            "Das eigene Verhalten oder Vorgehensweisen mit anderen Personen oder Lebewesen abstimmen und Regeln befolgen"]},
        {"title": "Konfliktfähigkeit – Konflikte lösen", "items": [
            "Die soziale Situation, die Stimmung, die Gefühle, die Spannung wahrnehmen",
            "In angespannten Situationen auch eigenständig handeln",
            "Möglichkeiten haben auch neue und andere Vorgehensweisen aufzunehmen und auszuprobieren"]},
        {"title": "Gestaltungskraft – Soziale Situationen mitgestalten", "items": [
            "Die Möglichkeit haben aktiv zu werden und handlungsfähig zu sein",
            "Die Möglichkeit haben Entscheidungen treffen zu können und über entsprechende Erfahrungen verfügen",
            "Sich einbringen, um Prozesse zu gestalten und etwas zu schaffen"]},
    ]},
    {"num": "V", "name": "Erwerben und nutzen", "unterpunkte": [
        {"title": "Orientierung in der Welt – sich in der Welt orientieren", "items": [
            "Die Welt wahrnehmen und sich in der Welt orientieren",
            "Die eigenen Erfahrungen ordnen und sich bezüglich Abläufe, Orten und Zeiten zurechtfinden",
            "Die erlebten Situationen beurteilen und vergleichen und sich entsprechend den Erkenntnissen organisieren"]},
        {"title": "Erschliessen der Welt – Selbständig neue Fähigkeiten erwerben", "items": [
            "In der Welt handeln und Informationen aufnehmen",
            "Sich die Welt erschliessen und Informationen nutzen",
            "Gesetzmässigkeiten erkennen, die zur Bewältigung des Alltags und Lebens wichtig sind"]},
        {"title": "Vorgehensweise und Strategien – Problemlösestrategien aneignen und nutzen", "items": [
            "Zweckmässige Vorgehensweisen und Strategien erwerben und entwickeln",
            "Zweckmässige Strategien erproben und anwenden",
            "Um Probleme, die sich im Leben stellen, wirksam angehen zu können"]},
    ]},
    {"num": "VI", "name": "Dranbleiben und bewältigen", "unterpunkte": [
        {"title": "Selbstständigkeit – Selbstständig den Alltag bewältigen", "items": [
            "Entwickeln von Selbstständigkeit, selbständig Handlungen ausführen, planen und kontrollieren",
            "Sich selbst regulieren, mit Gefühlen umgehen und aushalten können",
            "Selber Handlungen initiieren, Handlungsmotivation zeigen und eigene Ressourcen aktivieren"]},
        {"title": "Ausdauer – mit Ausdauer an Herausforderungen bleiben", "items": [
            "Ausdauer und Durchhaltevermögen entwickeln und zeigen",
            "Hindernisse überwinden in Bezug auf motorische, emotionale und kognitive Herausforderungen",
            "Eigene Ziele finden und verfolgen"]},
        {"title": "Flexibilität – flexibel auf äussere Einflüsse reagieren", "items": [
            "Flexibilität zeigen, die es erlaubt, sich neuen Begebenheiten anzupassen",
            "Lösungsvorschläge anderer aufnehmen und für eigene Problemlösungen nutzen",
            "Interesse an Neuem zeigen und entwickeln"]},
    ]},
]

# Überfachliche Kompetenzen im Lehrplan 21
LP21_UEBERFACHLICH = [
    "Personale Kompetenzen – Selbstreflexion",
    "Personale Kompetenzen – Selbstständigkeit",
    "Personale Kompetenzen – Eigenständigkeit",
    "Soziale Kompetenzen – Dialog- und Kooperationsfähigkeit",
    "Soziale Kompetenzen – Konfliktfähigkeit",
    "Soziale Kompetenzen – Umgang mit Vielfalt",
    "Methodische Kompetenzen – Sprachfähigkeit",
    "Methodische Kompetenzen – Informationen nutzen",
    "Methodische Kompetenzen – Aufgaben/Probleme lösen",
]

TITLE = "Förder- und Befähigungsschwerpunkte"
LP21_PLACEHOLDER = "[Ergänzen: LP21-Bezug]"


class SelectionError(ValueError):
    pass


def short_title(title: str) -> str:
    return title.split(" – ")[0].strip()


def parse_selection(raw_areas: list) -> list[dict]:
    """Prüft die Auswahl aus dem Formular und ergänzt sie mit den Katalogtexten."""
    by_num = {a["num"]: a for a in CATALOGUE}
    areas = []
    for raw in raw_areas or []:
        area = by_num.get(str(raw.get("num")))
        if not area:
            continue
        unterpunkte = []
        for up in raw.get("unterpunkte", []):
            try:
                cat_up = area["unterpunkte"][int(up.get("idx"))]
            except (ValueError, TypeError, IndexError):
                continue
            items = []
            for i in up.get("items", []):
                try:
                    items.append(cat_up["items"][int(i)])
                except (ValueError, TypeError, IndexError):
                    continue
            # Ohne Auswahl einzelner Punkte gelten alle drei
            unterpunkte.append({"title": cat_up["title"], "items": items or list(cat_up["items"])})
        if not unterpunkte:
            raise SelectionError(f"Bitte bei «{area['name']}» mindestens einen Unterpunkt anhaken.")
        lp21 = str(raw.get("lp21") or "auto")
        if lp21 != "auto" and lp21 not in LP21_UEBERFACHLICH:
            lp21 = "auto"
        areas.append({"num": area["num"], "name": area["name"], "unterpunkte": unterpunkte,
                      "notes": str(raw.get("notes", "")).strip(), "lp21": lp21})
    if not 1 <= len(areas) <= 3:
        raise SelectionError("Bitte 1 bis 3 Befähigungsbereiche wählen (empfohlen: 2–3).")
    order = [a["num"] for a in CATALOGUE]
    return sorted(areas, key=lambda a: order.index(a["num"]))


def build_header(areas: list[dict]) -> str:
    chosen = {a["num"] for a in areas}
    lines = ["## 2. Förder- und Befähigungsschwerpunkte", "### Besonders bedeutsame Befähigungsschwerpunkte"]
    lines += [f"{'[x]' if a['num'] in chosen else '[ ]'} {a['num']} {a['name']}" for a in CATALOGUE]
    lines += ["", "### Kommentar"]
    lines += [f"{a['name']} – {', '.join(short_title(u['title']) for u in a['unterpunkte'])}" for a in areas]
    lines += ["", "## 2–3 Förderschwerpunkte (Handlungsziele)"]
    return "\n".join(lines)


def area_query(area: dict) -> str:
    parts = [area["name"], area["notes"]]
    for u in area["unterpunkte"]:
        parts.append(u["title"])
        parts += u["items"]
    return "\n".join(parts)


def build_area_messages(*, area: dict, student: dict, period: str, general_notes: str,
                        student_context: str, kb_context: str) -> list[dict]:
    """Kurzer, fokussierter Auftrag für einen Bereich. Unterlagen stehen vorne (für alle
    Bereiche gleich, damit Ollama sie wiederverwenden kann), die Stichworte ganz am Schluss."""
    first = student["first_name"]
    parts = []
    if kb_context:
        parts.append("=== GRUNDLAGEN (Auszüge, z.B. Lehrplan 21) ===\n" + kb_context)
    if student_context:
        parts.append("=== FRÜHERE UNTERLAGEN ZUM KIND ===\n" + student_context)
    parts.append(
        "=== ANGABEN ===\n"
        f"Vorname: {first}\nKlasse/Stufe: {student.get('class_name') or '[unbekannt]'}\n"
        f"Planung für: {period or 'das nächste Schuljahr'}"
    )
    chosen = "\n".join(f"{u['title']}\n" + "\n".join(f"- {i}" for i in u["items"]) for u in area["unterpunkte"])
    parts.append(f"=== GEWÄHLTER BEFÄHIGUNGSBEREICH ===\n{area['num']} {area['name']}\n{chosen}")

    if area["lp21"] == "auto":
        lp21_rule = ("LP21:\n<genau EIN Begriff, wörtlich aus dieser Liste:\n"
                     + "\n".join(LP21_UEBERFACHLICH) + ">\n")
        was_rule = "WAS:\n<1–2 Sätze: was diese LP21-Kompetenz für " + first + " im nächsten Schuljahr konkret bedeutet>\n"
    else:
        lp21_rule = ""
        was_rule = f"WAS:\n<1–2 Sätze: was «{area['lp21']}» für {first} im nächsten Schuljahr konkret bedeutet>\n"

    parts.append(
        "=== AUFTRAG ===\n"
        f"Schreibe für den Ausblick auf das nächste Schuljahr drei kurze Texte zu genau diesem Befähigungsbereich. "
        f"Die Unterpunkte oben sind bereits gewählt; nenne sie nicht nochmals als Liste.\n"
        "Antworte GENAU in diesem Format, ohne weitere Texte, Überschriften oder Markdown:\n\n"
        f"AUSGANGSLAGE:\n<2–4 Sätze: konkrete Beobachtungen aus Stichworten und Unterlagen, warum dieser Bereich für {first} jetzt wichtig ist>\n"
        f"{lp21_rule}{was_rule}"
        f"WO:\n<2–3 Sätze im Stil «{first} wird mit Unterstützung von … in/bei … angehen.» "
        "Nenne die konkreten Situationen, Orte, Zeiten und Beteiligten aus den Stichworten.>\n\n"
        "Regeln: Gib jeden der Teile genau EINMAL aus, keine Varianten oder Alternativen. "
        "Verwende JEDES Stichwort zu diesem Bereich mindestens einmal. Erfinde nichts, was weder in den "
        "Stichworten noch in den Unterlagen steht. Wiederhole in WO nicht den Text von WAS."
    )
    if general_notes:
        parts.append("=== ALLGEMEINE STICHWORTE DER LEHRPERSON ===\n" + general_notes)
    parts.append(
        "=== STICHWORTE DER LEHRPERSON ZU DIESEM BEREICH (wichtigste und aktuellste Quelle) ===\n"
        + (area["notes"] or "(keine; stütze dich auf die Unterlagen)")
    )
    parts.append("Schreibe jetzt die Texte im verlangten Format.")
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": "\n\n".join(parts)}]


_LABELS = ("AUSGANGSLAGE", "LP21", "WAS", "WO")
# Grossgeschriebene Labels mit beliebigem Zusatz bis zum Doppelpunkt («WAS (Bezug LP21):»),
# kleingeschriebene nur exakt («Was:»), damit Sätze wie «Was ihm hilft: …» nicht als Label gelten.
_LABEL_RE = re.compile(
    r"^[\s*#>_-]*(?:(AUSGANGSLAGE|LP21|WAS|WO)\b[^:\n]{0,40}|(Ausgangslage|Lp21|Was|Wo)\s*)\**:[\s*]*(.*)$"
)


def parse_area_output(text: str) -> dict:
    """Zerlegt die Modellantwort in ihre Teile. Fehlende Teile bleiben leer."""
    result = {k: "" for k in _LABELS}
    current = None
    seen: set[str] = set()
    for line in text.splitlines():
        m = _LABEL_RE.match(line)
        if m:
            label = (m.group(1) or m.group(2)).upper()
            if label in seen:  # Modell beginnt eine zweite Variante: nur die erste verwenden
                break
            seen.add(label)
            current = label
            rest = m.group(3).strip()
            if rest:
                result[current] += rest + "\n"
            continue
        if current:
            result[current] += line + "\n"
    cleaned = {}
    for k, v in result.items():
        v = re.sub(r"\*\*|__", "", v).strip()
        cleaned[k] = re.sub(r"\n{3,}", "\n\n", v)
    if not any(cleaned.values()):  # Format nicht eingehalten: ganzen Text als Ausgangslage
        cleaned["AUSGANGSLAGE"] = text.strip()
    return cleaned


def match_lp21(text: str) -> str:
    """Ordnet die Modellantwort einem Begriff der LP21-Liste zu, sonst Platzhalter."""
    t = text.lower()
    for term in LP21_UEBERFACHLICH:
        if term.lower() in t:
            return term
    for term in LP21_UEBERFACHLICH:  # nur der Aspekt, z.B. «Selbstständigkeit»
        aspect = term.split(" – ")[1].lower()
        if aspect in t:
            return term
    return LP21_PLACEHOLDER


def assemble_area(n: int, area: dict, parts: dict) -> str:
    lp21 = area["lp21"] if area["lp21"] != "auto" else match_lp21(parts.get("LP21", ""))
    lines = [f"### {n} {area['name']}", "WOZU:", parts.get("AUSGANGSLAGE") or "[Ergänzen: Ausgangslage]", ""]
    for u in area["unterpunkte"]:
        lines.append(u["title"])
        lines += [f"- {i}" for i in u["items"]]
        lines.append("")
    lines += ["WAS (Bezug LP21):", lp21, parts.get("WAS") or "[Ergänzen: Bezug zum Kind]", ""]
    lines += ["WO – In welchem Kontext zu erlernen:", parts.get("WO") or "[Ergänzen: Lernsituation]"]
    return "\n".join(lines)
