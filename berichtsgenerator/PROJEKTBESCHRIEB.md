# Projektbeschrieb: Berichtsgenerator für die besondere Volksschule (Kanton Bern)

Stand: 3. Oktober 2026

Dieses Dokument fasst Ziel, Stand und offene Punkte zusammen, damit die Arbeit in einem neuen Chat
nahtlos weitergehen kann. **Für einen neuen Chat:** dieses Dokument und das aktuelle ZIP
(`berichtsgenerator.zip`) hochladen und schreiben: «Wir arbeiten am Berichtsgenerator weiter, hier ist der Projektbeschrieb.»

---

## 1. Ziel

Ein System, das **lokal auf einem Computer in der Schule** läuft und Lehrpersonen hilft, Berichte zu
verfassen, wie sie an einer Sonderschule bzw. in der besonderen Volksschule im Kanton Bern üblich sind:

- formative Beurteilungsberichte (nie summativ, keine Noten)
- Standortberichte, Lernberichte, Förderziele, Protokolle von Standortgesprächen,
  Kurzinformationen für Erziehungsberechtigte, Übertritts-/Übergabeberichte

Grundlagen für die Texte:

- **frühere Unterlagen zum Kind** (alte Beurteilungs- und Standortberichte, Förderpläne, Protokolle)
- **aktuelle Stichworte/Beobachtungen** der Lehrperson
- eine **Wissensbasis** mit kantonalen Vorgaben (BKD), Lehrplan 21, Schulkonzepten, anonymisierten Musterberichten

Rahmenbedingungen:

- **Kein Internet im Betrieb**: Es geht um besonders schützenswerte Personendaten. Das Sprachmodell läuft lokal (Ollama).
- **Mehrere Lehrpersonen** arbeiten gleichzeitig über den Browser im Schulnetz.
- Generierte Texte sind **Entwürfe**. Die Lehrperson prüft und verantwortet sie.

---

## 2. Aktueller Stand (funktioniert)

| Bereich | Umgesetzt |
|---|---|
| Anmeldung | persönliche Konten, Rollen Admin/Lehrperson, Sperre nach 8 Fehlversuchen, automatische Abmeldung nach 8 h |
| Dossiers | pro Kind; Lehrpersonen sehen nur freigegebene Dossiers, Admins sehen alle |
| Sammel-Import | Admin lädt Excel (.xlsx) oder CSV hoch (Vorname, Nachname, Jahrgang, Klasse, Lehrpersonen) → Dossiers inkl. Freigaben; Duplikate werden übersprungen |
| Unterlagen | Upload pro Dossier: Word .docx, PDF mit Text, TXT, RTF oder eingefügter Text; mit Art und Datum |
| Wissensbasis | allgemeine Dokumente (nur Admin), werden bei jedem Bericht nach Relevanz einbezogen |
| Bericht erstellen | Berichtsart wählen, Stichworte eintragen, Unterlagen ankreuzen → Text erscheint live |
| Überarbeiten mit KI | markierte Stelle oder ganzer Text: kürzer, ausführlicher, einfache Sprache, sachlicher, ressourcenorientierter, nur Rechtschreibung, eigene Anweisung |
| Finalisieren | finaler Bericht wird automatisch Grundlage für künftige Berichte |
| Export | Word-Datei mit Kopfzeilen und Unterschriftenzeile |
| Berichtsarten | 9 Vorlagen, in der Oberfläche durch Admins anpassbar, u.a. «Förderbericht (Felder für BU21 / BE-Login)» nach Leitfaden der Schule |
| Formulare | Häkchen in Word (Kontrollkästchen, alte Formularfelder, Wingdings-Symbole), Tabellen, Textfelder; ausgefüllte PDF-Formularfelder |
| Vorlagen-Abgleich | leere Formulare als «Leere Vorlage (für Abgleich)» in der Wissensbasis; beim Upload ins Dossier wird nur das Ausgefüllte/Angekreuzte übernommen (automatisch erkannt oder manuell gewählt, nachträglich neu abgleichbar) |
| Grundlagen-Auswahl | beim Erstellen einzelne Wissensbasis-Dokumente an-/abwählen; jedes gewählte Dokument erhält einen festen Anteil am Platz; unter dem Text wird angezeigt, aus welchen Dokumenten wie viele Abschnitte ans Modell gingen |
| Befähigungsschwerpunkte planen | eigene Seite pro Kind: Lehrperson wählt 1–3 Befähigungsbereiche, Unterpunkte, Unter-Unter-Punkte, Stichworte und LP21-Bezug pro Bereich; die App setzt Kästchen, Kommentar, Titel und Aufzählungen wörtlich aus dem Katalog (app/befaehigungen.py); das Modell schreibt pro Bereich nur Ausgangslage, WAS und WO (kurzer Auftrag, Stichworte zuletzt); ersetzt den langen Skill |
| Skills | gespeicherte Anweisungen pro Lehrperson, optional für alle geteilt; einfügbar beim Erstellen und Überarbeiten |
| Protokoll | wer wann welches Dossier angesehen, bearbeitet, exportiert hat |
| Löschen | ganzes Dossier inkl. aller Daten (Löschkonzept) |

**Regeln für das Modell** (Systemprompt in `app/prompts.py`): Schweizer Hochdeutsch ohne «ß», nur formativ
(keine Noten, keine Prädikate, keine Vergleiche), beobachtbar und ressourcenorientiert, nichts erfinden,
Fehlendes als `[Ergänzen: …]` markieren, keine Diagnosen, keine Wertungen der Familie.

---

## 3. Technik

- **Python-Webanwendung** (FastAPI, Jinja2-Vorlagen, reines HTML/CSS/JS ohne Internet-Abhängigkeiten)
- **SQLite-Datenbank** in `data/berichte.sqlite3` (enthält alle Personendaten)
- **Ollama** als lokaler Modell-Server; Standardmodell `gemma3:12b`
- **Suche in Unterlagen**: Passen die Unterlagen eines Kindes ins Kontextfenster, werden sie vollständig
  mitgegeben (neueste zuerst), sonst die relevantesten Abschnitte. Optional semantische Suche mit
  Embedding-Modell (`bge-m3`), sonst Stichwortsuche.
- läuft mit **Python 3.9 oder neuer** (auch dem auf Macs vorinstallierten Python)

Dateien:

```
berichtsgenerator/
  PROJEKTBESCHRIEB.md   dieses Dokument
  README.md             Installations- und Bedienungsanleitung
  start-mac.command     Start auf dem Mac (Doppelklick bzw. Rechtsklick → Öffnen)
  start.bat / start.sh  Start unter Windows / Linux
  docker-compose.yml    Variante für einen Linux-Server mit Docker
  .env.example          Vorlage für Einstellungen (.env)
  app/
    main.py        Webseiten und Schnittstellen
    prompts.py     Systemprompt, Berichtsarten, Überarbeitungsfunktionen
    retrieval.py   Auswahl der relevanten Unterlagen
    documents.py   Text aus PDF/Word/RTF/TXT lesen, in Abschnitte teilen
    importer.py    Sammel-Import von Schülerlisten
    llm.py         Anbindung an Ollama
    export.py      Word-Export
    auth.py        Passwörter (PBKDF2), Sitzungen, Rechte
    db.py          Datenbankschema
    cli.py         Kommandozeile: Benutzer, Passwort, Backup, Demo-Daten
    templates/     Seiten
    static/        Gestaltung und Browser-Skript
  tests/           automatische Tests (laufen ohne Modell)
```

Wichtige Einstellungen (`.env`): `BG_MODEL`, `BG_NUM_CTX` (Kontextlänge), `BG_EMBED_MODEL`,
`BG_SCHOOL_NAME`, `BG_DATA_DIR`. Details im README.

Code-Ablage: GitHub-Repository `chdietz1/rnbo`, Branch `claude/sweet-cori-xh117t`, Ordner `berichtsgenerator/`.
Die Projektleitung arbeitet nicht mit GitHub; Übergabe immer als **ZIP-Datei**.

---

## 4. Testumgebung (Projektleitung)

- **MacBook M2 mit 16 GB**, Ollama installiert
- Modell `gemma3:12b`, `BG_NUM_CTX=8192`, ohne Embedding-Modell (spart Arbeitsspeicher)
- Start über `start-mac.command`; App nur auf dem Mac erreichbar (`127.0.0.1:8000`)
- Demo-Konto: Benutzername `demo`, Passwort `demo-passwort`, Beispielschülerin «Lina Beispiel» (erfunden)
- Ergebnis bisher: Demo läuft, Geschwindigkeit gut, Import funktioniert
- Erster realer Test: Ergebnis «nicht so schlecht». Hauptproblem waren standardisierte Formulare, die nur
  teilweise ausgefüllt sind, und nicht erkannte Häkchen → Vorlagen-Abgleich und Häkchen-Erkennung eingebaut
  (noch nicht mit echten Formularen der Schule getestet)
- Wissensbasis der Schule (bisher): «Leitfaden Beurteilungs-/Förderberichte 2025/26» (BU21, BE-Login,
  Standardtext «Allgemeine Anmerkungen»), «Zeitplan Beurteilungsberichte», «Befähigungsbereiche und deren Inhalte» (PDF).
  Mit 8192 Tokens Kontext passen nur ca. 4'000 Zeichen Wissensbasis pro Bericht; der Standardtext wird gefunden,
  die Befähigungsbereiche nicht immer. Grösserer Rechner/Kontext hilft.
- Skill «Ausblick Befähigungsschwerpunkte (WOZU / WAS / WO)» mit Befähigungskatalog im Originalwortlaut
  (ca. 8'500 Zeichen). Bei 8192 Tokens bleiben damit nur ca. 4'500 Zeichen für Unterlagen → Empfehlung
  BG_NUM_CTX=16384, falls der Mac genug Speicher hat.
- Offizielles Formular «Förderbericht besonderes Volksschulangebot 7./8./9. Schuljahr» (BU21/2023.01,
  Ansichtsexemplar) erhalten; die Berichtsart «Förderbericht (Felder für BU21 / BE-Login)» folgt genau seinen
  Feldern (Allgemeine Anmerkungen, Fachliche Kompetenzen pro Fach, Personale/Soziale/Methodische Kompetenzen mit
  den zugeordneten Befähigungsbereichen, Ausblick/Ressourcen/Massnahmen) plus Förderschwerpunkte der Titelseite.
- PDF-Lesen: pro Seite automatisch Layout-Modus (richtige Reihenfolge bei Formularen) oder einfacher Modus
  (wenn der Layout-Modus Wörter zerreisst). Beim Vorlagen-Abgleich werden mehrfach vorkommende Vorlagenzeilen
  (Platzhalter, Kopfzeilen) ignoriert.
- **Ausstehend:** echter Test mit realen (bzw. anonymisierten) Unterlagen, um zu prüfen, ob das Modell
  die Unterlagen wirklich einbezieht und nichts erfindet

Zum Aktualisieren auf eine neue Version: neues ZIP an anderem Ort entpacken, den Ordner `data` und die
versteckte Datei `.env` aus dem alten Ordner hineinverschieben, alten Ordner löschen.

Demos zum Zeigen ohne Installation:

- Online (privat, über «Teilen» freigeben): https://claude.ai/artifact/TS4DKTAMq8d2jKrnrWAdhA
- Offline: Datei `Berichtsgenerator-Demo.html` (Doppelklick, läuft im Browser ohne Internet)

---

## 5. Hardware für den Schulbetrieb (Überlegungen)

| Variante | Einschätzung |
|---|---|
| PC mit NVIDIA RTX 5090 (32 GB), 64 GB RAM, 2 TB SSD, ca. CHF 4'000–5'000 | schnellste Lösung, 3–5 Lehrpersonen gleichzeitig flüssig; laut, viel Strom |
| Mac mini M5 Pro, 64 GB, 2 TB (in Prüfung) | geeignet für 2–3 gleichzeitig, leise, sparsam; Modelle bis ca. 27–32 Mrd. Parameter; bei vielen Unterlagen längere «Denkpause» vor dem Schreiben |
| Mac Studio (64–96 GB) | Zwischenlösung: leise und schneller als Mac mini |

Grundsätze: mindestens 64 GB (beim Mac nicht aufrüstbar), Festplattenverschlüsselung (FileVault/BitLocker),
Netzwerkkabel, feste IP, USV, verschlüsselte Backups, abschliessbarer Standort, Schulinformatik früh einbeziehen.

---

## 6. Bekannte Einschränkungen

- Alte Word-Dateien `.doc` und Pages-Dateien werden nicht gelesen (vorher als .docx speichern).
- Gescannte PDFs ohne Text werden nicht gelesen (keine Texterkennung/OCR).
- Vorlagen-Abgleich bei PDFs funktioniert nur, wenn Vorlage und ausgefülltes PDF gleich aufgebaut sind;
  bei «flachen» PDFs (ausgedruckt und gescannt, oder als Bild) nicht.
- Unterlagen nur einzeln hochladbar.
- Nach einem Update bleibt man angemeldet, wenn der Ordner `data` übernommen wird (der Sitzungsschlüssel
  liegt dort). **Bewusst so belassen** (Demo); vor dem Schulbetrieb prüfen.
- Demo-Konto mit bekanntem Passwort: vor dem Einsatz mit echten Daten Passwort ändern bzw. eigenes Admin-Konto
  anlegen und Demo-Konto sperren.
- Für den Betrieb im Schulnetz muss in `start-mac.command` `127.0.0.1` durch `0.0.0.0` ersetzt werden,
  idealerweise mit HTTPS (Reverse Proxy).
- Ein echter Test mit grossem Sprachmodell wurde in der Entwicklungsumgebung nie gemacht (nur Tests mit
  nachgebautem Ollama); die Projektleitung testet auf dem eigenen Mac.

---

## 7. Mögliche nächste Schritte (Ideen-Speicher)

- Vorlagen-Abgleich mit echten Formularen der Schule testen (leere + ausgefüllte Version)
- Auswertung des echten Tests; Anweisungen an das Modell (Systemprompt, Berichtsarten) nachschärfen,
  idealerweise mit anonymisierten Musterberichten der Schule
- Berichtsarten an die offiziellen Vorlagen der Schule bzw. der BKD anpassen
- mehrere Unterlagen auf einmal hochladen
- Unterstützung für .doc-Dateien und Texterkennung für gescannte PDFs
- Word-Export mit Schul-Layout (Logo, Vorlage .dotx)
- Versionsverlauf von Berichten (wer hat was geändert)
- Betrieb als Dienst mit automatischem Start, HTTPS, regelmässiges automatisches Backup
- Vorbereitung für die Schulinformatik/Datenschutz: Kurzdokumentation zu Datenflüssen und Löschkonzept
- Hardware-Entscheid und Beschaffungsantrag

---

## 8. Verlauf der Entwicklung

1. Grundsystem gebaut (Web-App, Dossiers, Upload, Wissensbasis, Generieren, Überarbeiten, Word-Export, Rechte, Protokoll)
2. Klickbare Demo (online und als Offline-HTML-Datei)
3. Hardware-Beratung (PC mit RTX vs. Mac mini/Studio)
4. Mac-Startdatei, Demo-Daten, Unterstützung für Python 3.9
5. Fehler behoben: Anmeldung auf dem Mac schlug fehl (Passwortverfahren scrypt fehlt im Mac-Python → PBKDF2)
6. Sammel-Import von Dossiers aus Excel/CSV
7. Häkchen-Erkennung, Abgleich mit leeren Vorlagen, Skills, Berichtsart «Förderbericht BU21»
8. Skills-Seite mit sichtbaren Knöpfen; Wissensbasis-Auswahl mit fairer Platzverteilung und Quellenanzeige (LP21-Bezug kam vorher nicht beim Modell an)
9. Platzberechnung zieht die Länge von Auftrag, Stichworten und Skills ab (vorher lief die Anfrage bei langen Skills über das Kontextfenster); Anzeige «Umfang der Anfrage: ca. X von Y Tokens»
10. Seite «Befähigungsschwerpunkte planen» (der lange Ein-Schritt-Skill überforderte das 12B-Modell: erfundene Unterpunkte, ignorierte Stichworte); bei allen Berichtsarten stehen die Stichworte jetzt am Schluss der Anfrage
11. Befähigungsschwerpunkte: Modell schrieb das Format mehrfach (Varianten) → nur erste Variante übernehmen, «genau einmal» im Auftrag, Antwortlänge pro Bereich begrenzt (num_predict 900)
