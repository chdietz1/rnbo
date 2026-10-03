"""Systemprompt und Standard-Berichtsarten.

Die Berichtsarten werden beim ersten Start in die Datenbank geschrieben und
können danach von Administratorinnen/Administratoren in der Oberfläche
angepasst werden (Menü «Verwaltung → Berichtsarten»).

Hinweis: Die Strukturen orientieren sich an der gängigen Praxis der
besonderen Volksschule im Kanton Bern (formative Beurteilung, Förderplanung,
Standortgespräche, Lehrplan 21 inkl. überfachlicher Kompetenzen). Bitte mit
den aktuell gültigen Vorgaben der BKD und des eigenen Schulkonzepts
abgleichen und bei Bedarf anpassen.
"""
from __future__ import annotations

SYSTEM_PROMPT = """Du bist eine erfahrene schulische Heilpädagogin bzw. ein erfahrener schulischer Heilpädagoge an einer Schule der besonderen Volksschule (Sonderschule) im Kanton Bern. Du unterstützt Lehrpersonen beim Verfassen von Berichten über Schülerinnen und Schüler.

Verbindliche Regeln:
1. Schreibe in Schweizer Hochdeutsch: kein «ß», sondern immer «ss». Verwende Schweizer Schulbegriffe (z.B. Lehrperson, Erziehungsberechtigte, Schulische Heilpädagogik, Förderplanung, Standortgespräch).
2. Die Beurteilung ist ausschliesslich formativ: beschreibend, lern- und entwicklungsorientiert. Verwende keine Noten, keine Prädikate (wie «genügend», «gut», «ungenügend») und keine Vergleiche mit anderen Kindern.
3. Beschreibe beobachtbares Verhalten und konkrete Lernfortschritte, bezogen auf die individuellen Lern- und Förderziele. Formuliere ressourcen- und stärkenorientiert, wertschätzend und respektvoll, aber ehrlich; benenne Herausforderungen sachlich als nächste Entwicklungsschritte.
4. Verwende AUSSCHLIESSLICH Informationen aus den bereitgestellten Unterlagen (frühere Berichte, Förderpläne, Beobachtungen der Lehrperson) und den kantonalen Grundlagen. Erfinde keine Fakten, Diagnosen, Testergebnisse, Daten oder Zitate. Wo Informationen fehlen, setze einen gut sichtbaren Platzhalter in eckigen Klammern, z.B. [Ergänzen: Beobachtung zum Zahlenraum].
5. Aktuelle Beobachtungen der Lehrperson haben Vorrang vor älteren Berichten. Ältere Berichte dienen dazu, Entwicklungen und Fortschritte sichtbar zu machen.
6. Schreibe für Erziehungsberechtigte und Fachpersonen verständlich. Fachbegriffe nur, wenn nötig, und dann kurz erklärt.
7. Nenne das Kind mit seinem Vornamen. Keine Wertungen der Familie. Keine medizinischen oder psychologischen Diagnosen stellen.
8. In den Unterlagen bedeutet «[x]» angekreuzt und «[ ]» nicht angekreuzt. Nur angekreuzte Optionen gelten. Steht «(Auszug: nur ausgefüllte Teile)» bei einer Unterlage, wurden leere Teile eines Formulars entfernt; die Zeile vor einem Eintrag ist jeweils die Frage oder Überschrift aus dem Formular.
9. Formatierung: Überschriften mit «## », Unterüberschriften mit «### », Aufzählungen mit «- ». Kein weiteres Markdown (keine Tabellen, kein Fettdruck).
"""


DEFAULT_REPORT_TYPES = [
    {
        "key": "beurteilungsbericht",
        "name": "Beurteilungsbericht (formativ)",
        "description": "Ausführlicher, formativer Bericht über eine Beurteilungsperiode.",
        "instructions": """Verfasse einen formativen Beurteilungsbericht für die angegebene Periode mit folgender Struktur:

## Ausgangslage
Kurz: Klasse/Stufe, Schulungsform, Rahmen der Förderung, gültige Förderziele der Periode (nur soweit aus den Unterlagen bekannt).

## Entwicklung in den Fachbereichen
Pro Fachbereich bzw. Förderbereich, zu dem Informationen vorliegen (z.B. Sprache/Deutsch, Mathematik, NMG, Gestalten, Bewegung und Sport, Musik), je eine Unterüberschrift «### ». Beschreibe Stand, Fortschritte im Vergleich zu früher und Bezug zu den individuellen Lernzielen.

## Überfachliche Kompetenzen
### Personale Kompetenzen
(Selbstreflexion, Selbstständigkeit, Eigenständigkeit)
### Soziale Kompetenzen
(Dialog- und Kooperationsfähigkeit, Konfliktfähigkeit, Umgang mit Vielfalt)
### Methodische Kompetenzen
(Sprachfähigkeit, Informationen nutzen, Aufgaben/Probleme lösen)

## Lern- und Arbeitsverhalten

## Stärken und Ressourcen

## Ausblick und nächste Entwicklungsschritte
Konkrete, erreichbare nächste Schritte bzw. Vorschläge für Förderziele.""",
    },
    {
        "key": "foerderbericht_bu21",
        "name": "Förderbericht (Felder für BU21 / BE-Login)",
        "description": "Texte pro Feld zum Einfügen in die Beurteilungsapp, mit Auswertung der Förderschwerpunkte.",
        "instructions": """Verfasse die Texte für den Förderbericht in der Beurteilungsapp (BU21 im BE-Login). Jeder Abschnitt wird einzeln in ein Feld der App kopiert. Schreibe darum pro Abschnitt einen in sich verständlichen Text.

## Förderschwerpunkte
1–3 Förderschwerpunkte aus der Bildungsplanung bzw. den Handlungszielen der Standortgespräche (STAO), je ein kurzer, klarer Satz. Nur Schwerpunkte, die in den Unterlagen stehen. Hier noch keine Auswertung.

## Allgemeine Anmerkungen zur aktuellen Lebens- und Schulsituation
Falls die Grundlagen (Leitfaden der Schule) einen Standardtext für dieses Feld enthalten, übernimm ihn wörtlich. Sonst: [Ergänzen: Standardtext der Schule]. Danach höchstens 1–2 Sätze zur aktuellen Situation des Kindes, falls aus den Unterlagen bekannt.

## Personale Kompetenzen
## Soziale Kompetenzen
## Methodische Kompetenzen
Für jedes dieser drei Felder:
- Bezieht sich der Text auf einen Förderschwerpunkt, beginne mit «(vgl. Förderschwerpunkte)» und werte ihn kurz aus: Was konnte erreicht werden, was noch nicht? Wird der Förderschwerpunkt für das nächste Schuljahr beibehalten?
- Jedes Feld braucht Inhalt. Ergänze bei Bedarf weitere beobachtete Kompetenzen, auch positive oder weitere Lernfelder, gern mit Bezug zu den Befähigungsbereichen (z.B. «Sich austauschen und dazugehören», «Dranbleiben und bewältigen»), falls diese in den Grundlagen stehen.
- 3–6 Sätze pro Feld, konkret und beobachtbar.

## Ausblick, Ressourcen, Massnahmen
Kurz. Möglich ist der Satz: «Ressourcen und gezielte Fördermassnahmen sind dem STAO-Bericht zu entnehmen.» Einen Austritt oder ein 10. Schuljahr hier erwähnen, falls aus den Unterlagen bekannt.""",
    },
    {
        "key": "standortbericht",
        "name": "Standortbericht (Vorbereitung Standortgespräch)",
        "description": "Bericht zur Vorbereitung eines schulischen Standortgesprächs.",
        "instructions": """Verfasse einen Standortbericht zur Vorbereitung des schulischen Standortgesprächs mit folgender Struktur:

## Anlass und Ausgangslage

## Rückblick auf die bisherigen Förderziele
Für jedes bisherige Ziel (soweit bekannt): Ziel, Einschätzung der Zielerreichung (beschreibend, z.B. «erreicht», «teilweise erreicht», «noch nicht erreicht» mit Begründung durch Beobachtungen).

## Aktueller Stand in den Entwicklungsbereichen
Nur Bereiche, zu denen Informationen vorliegen, je mit «### »:
Lernen und Wissensanwendung; Allgemeine Aufgaben und Anforderungen; Kommunikation; Bewegung und Mobilität; Für sich selbst sorgen; Umgang mit Menschen; Freizeit, Erholung und Gemeinschaft; sowie schulische Fachbereiche.

## Stärken und Ressourcen

## Vorschläge für neue Förderziele
2–4 Ziele, konkret, beobachtbar und überprüfbar formuliert (Wer? Was? Bis wann? Woran erkennbar?).

## Offene Fragen und Themen für das Gespräch""",
    },
    {
        "key": "lernbericht",
        "name": "Lernbericht (kurz)",
        "description": "Kompakter Bericht (ca. 1 Seite), z.B. zum Semesterende.",
        "instructions": """Verfasse einen kompakten Lernbericht (ca. 350–500 Wörter) mit folgender Struktur:

## Lernen und Fortschritte

## Arbeits- und Sozialverhalten

## Das gelingt schon gut

## Daran arbeiten wir weiter""",
    },
    {
        "key": "foerderziele",
        "name": "Förderziele formulieren",
        "description": "Vorschläge für überprüfbare Förder- bzw. Lernziele.",
        "instructions": """Formuliere Vorschläge für Förderziele für die nächste Förderperiode.

## Förderziele
Für 3–5 Ziele jeweils:
### Ziel <Nummer>: <Bereich>
- Zielformulierung: konkret, positiv, beobachtbar (SMART)
- Indikatoren: Woran erkennen wir, dass das Ziel erreicht ist?
- Massnahmen/Unterstützung in der Schule
- Mögliche Beiträge des Umfelds (falls sinnvoll)
- Überprüfung: wann und wie

Begründe kurz jeweils mit Bezug auf die Unterlagen, warum dieses Ziel jetzt sinnvoll ist.""",
    },
    {
        "key": "protokoll_ssg",
        "name": "Protokoll Standortgespräch (aus Stichworten)",
        "description": "Ausformuliertes Protokoll aus den Gesprächsnotizen.",
        "instructions": """Erstelle aus den Stichworten der Lehrperson (Beobachtungen/Notizen) ein sachliches Protokoll eines schulischen Standortgesprächs. Gib nur wieder, was in den Notizen steht; erfinde keine Aussagen.

## Rahmen
Datum, Teilnehmende, Anlass (Platzhalter, falls nicht in den Notizen).

## Einschätzungen der Beteiligten

## Gemeinsame Sicht und Vereinbarungen

## Förderziele und Massnahmen

## Verantwortlichkeiten und nächste Schritte

## Nächstes Gespräch""",
    },
    {
        "key": "elterninfo",
        "name": "Kurzinformation für Erziehungsberechtigte",
        "description": "Kurzer, gut verständlicher Text in einfacher Sprache.",
        "instructions": """Schreibe eine kurze, freundliche Information für die Erziehungsberechtigten (ca. 150–250 Wörter) in einfacher, gut verständlicher Sprache. Kurze Sätze, keine Fachbegriffe. Beginne mit einer positiven Beobachtung. Direkte Anrede («Liebe Erziehungsberechtigte» bzw. Platzhalter für Namen).""",
    },
    {
        "key": "uebertritt",
        "name": "Übertritts-/Übergabebericht",
        "description": "Bericht für die aufnehmende Lehrperson bzw. Institution.",
        "instructions": """Verfasse einen Übergabebericht für die aufnehmende Lehrperson bzw. Institution mit folgender Struktur:

## Schulische Laufbahn und Rahmen

## Aktueller Lern- und Entwicklungsstand
Mit Unterüberschriften «### » pro Bereich, zu dem Informationen vorliegen.

## Was sich bewährt hat
Hilfreiche Methoden, Strukturen, Hilfsmittel und Unterstützungsformen.

## Stärken, Interessen und Ressourcen

## Hinweise für den Übergang
Wichtige Absprachen, laufende Förderziele, Bezugspersonen (nur soweit bekannt).""",
    },
    {
        "key": "frei",
        "name": "Freier Auftrag",
        "description": "Eigene Anweisung im Feld «Zusätzliche Anweisungen».",
        "instructions": """Erfülle den Auftrag aus den zusätzlichen Anweisungen der Lehrperson. Halte dich an alle allgemeinen Regeln.""",
    },
]


REVISE_ACTIONS = {
    "kuerzer": "Kürze den Text deutlich (etwa um ein Drittel), ohne wichtige Inhalte zu verlieren.",
    "ausfuehrlicher": "Formuliere den Text etwas ausführlicher und konkreter, ohne neue Fakten zu erfinden. Wo Beispiele fehlen, setze Platzhalter [Ergänzen: Beispiel].",
    "einfach": "Formuliere den Text in einfacher, gut verständlicher Sprache für Erziehungsberechtigte (kurze Sätze, keine Fachbegriffe).",
    "sachlich": "Formuliere den Text sachlicher und neutraler, beschreibend statt wertend.",
    "ressourcen": "Formuliere den Text stärker ressourcen- und entwicklungsorientiert, ohne Schwierigkeiten zu verschweigen.",
    "korrektur": "Korrigiere nur Rechtschreibung, Grammatik und Zeichensetzung (Schweizer Rechtschreibung, kein ß). Inhalt und Stil unverändert lassen.",
}


def build_generation_messages(
    *,
    report_type: dict,
    student: dict,
    period: str,
    observations: str,
    extra: str,
    student_context: str,
    kb_context: str,
) -> list[dict]:
    parts = []
    if kb_context:
        parts.append(
            "=== KANTONALE GRUNDLAGEN / SCHULINTERNE VORGABEN (Auszüge) ===\n" + kb_context
        )
    if student_context:
        parts.append(
            "=== FRÜHERE UNTERLAGEN ZUM KIND (Berichte, Förderpläne, Protokolle) ===\n"
            + student_context
        )
    parts.append(
        "=== ANGABEN ===\n"
        f"Vorname: {student['first_name']}\n"
        f"Klasse/Stufe: {student.get('class_name') or '[unbekannt]'}\n"
        f"Jahrgang: {student.get('birth_year') or '[unbekannt]'}\n"
        f"Berichtsperiode / Datum: {period or '[unbekannt]'}"
    )
    parts.append(
        "=== AKTUELLE BEOBACHTUNGEN UND NOTIZEN DER LEHRPERSON ===\n"
        + (observations.strip() or "(keine zusätzlichen Beobachtungen angegeben)")
    )
    parts.append("=== AUFTRAG ===\n" + report_type["instructions"])
    if extra.strip():
        parts.append("=== ZUSÄTZLICHE ANWEISUNGEN DER LEHRPERSON ===\n" + extra.strip())
    parts.append(
        "Schreibe jetzt den Text. Gib nur den Text selbst aus, ohne Vorbemerkung oder Kommentar."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(parts)},
    ]


def build_revise_messages(text: str, instruction: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Überarbeite den folgenden Text.\nAnweisung: {instruction}\n"
            "Gib nur den überarbeiteten Text aus, ohne Kommentar. Behalte die Formatierung "
            "(Überschriften mit ##, Aufzählungen mit -) bei.\n\n=== TEXT ===\n" + text,
        },
    ]
