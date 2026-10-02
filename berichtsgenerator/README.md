# Berichtsgenerator für die besondere Volksschule (Kanton Bern)

Webanwendung, die **lokal auf einem Schulcomputer** läuft und Lehrpersonen hilft,
**formative Berichte** zu verfassen: Beurteilungsberichte, Standortberichte, Lernberichte,
Förderziele, Protokolle von Standortgesprächen, Elterninformationen und Übergabeberichte.

Grundlage für die Texte sind:

- **frühere Unterlagen zum Kind** (alte Beurteilungs- und Standortberichte, Förderpläne, Protokolle),
- **aktuelle Beobachtungen/Stichworte** der Lehrperson,
- eine **Wissensbasis** mit kantonalen Vorgaben, Leitfäden, Lehrplan 21 und Schulkonzepten.

Das Sprachmodell läuft über [Ollama](https://ollama.com) **auf dem gleichen Rechner**.
Im Betrieb wird **keine Internetverbindung** gebraucht und es gehen keine Daten nach aussen.
Mehrere Lehrpersonen arbeiten gleichzeitig über den Browser im Schulnetz.

> Generierte Texte sind **Entwürfe**. Die Lehrperson prüft, ergänzt und verantwortet jeden Bericht.
> Das Modell ist angewiesen, nichts zu erfinden und fehlende Angaben als `[Ergänzen: …]` zu markieren.

---

## Funktionen

| Bereich | Was es kann |
|---|---|
| Dossiers | Schülerinnen/Schüler erfassen; Zugriff nur für freigegebene Lehrpersonen |
| Unterlagen | PDF (mit Text), Word (.docx), TXT, RTF hochladen oder Text einfügen |
| Berichte erstellen | Berichtsart wählen, Beobachtungen eintragen, Unterlagen auswählen → Text wird live geschrieben |
| Überarbeiten | Markierte Stelle oder ganzen Text: kürzer, ausführlicher, einfache Sprache, sachlicher, ressourcenorientierter, Rechtschreibung, eigene Anweisung |
| Finalisieren | Finale Berichte werden automatisch als Grundlage für künftige Berichte abgelegt |
| Export | Word-Datei (.docx) mit Kopfzeilen, Überschriften und Unterschriftenzeile |
| Berichtsarten | Aufbau und Anweisungen pro Berichtsart in der Oberfläche anpassbar |
| Sicherheit | Anmeldung, Rollen (Admin/Lehrperson), Zugriffsprotokoll, CSRF-Schutz, Sperre nach Fehlversuchen |

---

## 1. Hardware

Die Textqualität und Geschwindigkeit hängen vor allem von der Grafikkarte bzw. vom Arbeitsspeicher ab.

| Ausstattung | Empfohlenes Modell (`BG_MODEL`) | Hinweis |
|---|---|---|
| PC mit NVIDIA-Grafikkarte **16 GB** (z.B. RTX 4060 Ti 16 GB) | `gemma3:12b` (Standard) oder `qwen3:14b` | gute Qualität, ca. 1–2 Min. pro Bericht |
| NVIDIA **24 GB** oder Mac mit Apple Silicon ab **32 GB** RAM | `mistral-small3.2` (24B) oder `gemma3:27b` | deutlich bessere Formulierungen |
| Nur Prozessor, 32 GB RAM | `gemma3:4b` | funktioniert, aber langsam und schwächer |

Modelle entwickeln sich schnell. Am besten zwei, drei Modelle mit anonymisierten Beispieldaten
vergleichen und das beste in `.env` eintragen. Deutsch, und zwar ohne «ß», ist das wichtigste Kriterium.

## Schnellstart auf einem Mac (zum Ausprobieren)

Voraussetzung: [Ollama](https://ollama.com/download) ist installiert. Für einen Mac mit 16 GB ist das
Modell `gemma3:12b` mit verkürztem Kontext voreingestellt.

1. ZIP entpacken.
2. Rechtsklick auf **`start-mac.command`** → **Öffnen** → nochmals **Öffnen** bestätigen
   (macOS fragt das beim ersten Mal, weil die Datei aus dem Internet stammt).
   Alternativ im Terminal: `bash start-mac.command`
3. Beim ersten Start werden das Sprachmodell (ca. 8 GB) und die Python-Pakete heruntergeladen.
   Das dauert je nach Internetverbindung 10–30 Minuten. Fehlt Python, öffnet sich die Download-Seite.
4. Der Browser öffnet `http://localhost:8000`. Anmelden mit **demo** / **demo-passwort**.
   Eine erfundene Beispielschülerin «Lina Beispiel» mit drei Unterlagen ist bereits angelegt.

Für den Test ist die App nur auf diesem Mac erreichbar. Andere Programme möglichst schliessen,
damit das Modell genug Arbeitsspeicher hat. Ist es zu langsam, in der Datei `.env`
`BG_MODEL=gemma3:4b` eintragen (schneller, aber schwächere Texte).

## 2. Installation (einmalig, mit Internet)

Für die Installation braucht es **einmal** Internet (Programme und Modelle herunterladen).
Danach kann der Rechner vom Internet getrennt werden.

### Variante A: Windows oder Linux ohne Docker

1. **Ollama** installieren: <https://ollama.com/download>
2. Modelle herunterladen (Eingabeaufforderung):
   ```
   ollama pull gemma3:12b
   ollama pull bge-m3
   ```
3. **Python 3.9 oder neuer** installieren (<https://www.python.org>, bei Windows «Add to PATH» ankreuzen).
4. Diesen Ordner auf den Rechner kopieren, `.env.example` nach `.env` kopieren und den Schulnamen eintragen.
5. Starten:
   - Windows: Doppelklick auf `start.bat`
   - Linux/macOS: `./start.sh`

   Beim ersten Start werden die Python-Pakete installiert.
6. Im Browser `http://localhost:8000` öffnen und das **Administrationskonto** anlegen.

### Variante B: Docker (Linux-Server)

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec ollama ollama pull gemma3:12b
docker compose exec ollama ollama pull bge-m3
```

### Zugriff aus dem Schulnetz

Die anderen Lehrpersonen öffnen `http://<IP-des-Rechners>:8000`, z.B. `http://192.168.1.50:8000`.

- Die Firewall muss **Port 8000 nur aus dem internen Netz** erlauben.
- Ollama (Port 11434) darf **nicht** von aussen erreichbar sein. Standardmässig hört es nur auf `localhost`.
- Für den Dauerbetrieb den Start als Dienst einrichten (Windows: Aufgabenplanung «Beim Start»; Linux: systemd).
- Mehrere gleichzeitige Anfragen verarbeitet Ollama nacheinander oder parallel (`OLLAMA_NUM_PARALLEL`).
  Bei vielen Nutzenden entsprechend mehr Grafikspeicher einplanen.

## 3. Erste Schritte

1. **Benutzer** anlegen (Menü «Benutzer»): eine Person pro Lehrperson, keine Sammelkonten.
2. **Wissensbasis** füllen (Menü «Wissensbasis», nur Admin). Die Dokumente einmal herunterladen und hochladen, zum Beispiel:
   - Vorgaben und Leitfäden zur **Beurteilung in der Volksschule** der Bildungs- und Kulturdirektion (BKD) des Kantons Bern (bkd.be.ch)
   - Unterlagen zur **besonderen Volksschule** bzw. Sonderschulung im Kanton Bern (BKD)
   - **Lehrplan 21 Kanton Bern** (be.lehrplan.ch), mindestens die überfachlichen Kompetenzen und die relevanten Fachbereiche
   - Unterlagen zum **schulischen Standortgespräch**
   - **Schulinterne** Beurteilungskonzepte, Vorlagen und anonymisierte **Musterberichte** (verbessern den Stil stark)

   In der Wissensbasis **keine Personendaten** ablegen.
3. Unter **Berichtsarten** Aufbau und Formulierungen an die Vorlagen der Schule anpassen.
4. Pro Kind ein **Dossier** anlegen, alte Berichte hochladen und Kolleginnen/Kollegen freigeben.
5. **Bericht erstellen**: Berichtsart wählen, Beobachtungen stichwortartig eintragen, generieren, überarbeiten, speichern, finalisieren, als Word exportieren.

**Tipps für gute Ergebnisse**

- Konkrete Beobachtungen bringen mehr als allgemeine Aussagen («liest Zweisilber mit Silbenbögen selbstständig» statt «Lesen besser»).
- Gescannte PDFs enthalten keinen Text. Solche Berichte als Word-Datei hochladen oder den Text einfügen.
- Sehr viele oder lange Unterlagen werden gekürzt: Das System wählt dann die relevantesten Abschnitte.
  Mit `BG_NUM_CTX=32768` (mehr Grafikspeicher nötig) passt mehr hinein.

## 4. Datenschutz (besonders schützenswerte Personendaten)

Die Anwendung ist so gebaut, dass die Daten die Schule nicht verlassen. Die Schule bleibt trotzdem für
den Betrieb verantwortlich (kantonales Datenschutzgesetz, KDSG Bern). Empfehlungen:

- **Festplattenverschlüsselung** auf dem Server aktivieren (Windows: BitLocker; Linux: LUKS).
  Die Datenbank `data/berichte.sqlite3` enthält alle Dossiers.
- Server **physisch geschützt** aufstellen (abschliessbarer Raum) und Bildschirmsperre aktivieren.
- **Kein Internetzugang** im Betrieb oder Firewall-Regel «nur ausgehend blockieren». Updates bewusst und geplant einspielen.
- **Starke Passwörter**, persönliche Konten; ausgetretene Personen sofort sperren.
- **Zugriffsprotokoll** (Menü «Protokoll») regelmässig prüfen.
- **Löschkonzept**: Dossiers nach Ablauf der Aufbewahrungsfrist löschen (Dossier → «Dossier löschen» entfernt alles).
- **Backups** verschlüsselt aufbewahren (siehe unten).
- Bei Betrieb über WLAN oder in einem grösseren Netz: HTTPS mit einem Reverse Proxy (z.B. Caddy) vorschalten und `BG_HTTPS_ONLY=1` setzen.
- Vor der Einführung Schulleitung und ggf. die kantonale Datenschutzaufsicht bzw. die IT-Verantwortlichen einbeziehen.

## 5. Betrieb

```bash
# Sicherung der Datenbank (konsistent, auch im laufenden Betrieb)
python -m app.cli backup D:\Sicherung

# Passwort zurücksetzen / Benutzer auf der Kommandozeile anlegen
python -m app.cli reset-password admin
python -m app.cli create-user mmuster "Maria Muster" --admin

# Testkonto «demo» mit erfundenen Beispieldaten anlegen
python -m app.cli demo
```

(Unter Windows vorher `.venv\Scripts\activate`, unter Linux `source .venv/bin/activate` ausführen.)

**Modell wechseln:** mit `ollama pull <modell>` herunterladen, `BG_MODEL` in `.env` ändern und neu starten.
Wird das Embedding-Modell gewechselt, in der Wissensbasis «Alles neu indexieren» ausführen.

## 6. Einstellungen (`.env`)

| Variable | Standard | Bedeutung |
|---|---|---|
| `BG_SCHOOL_NAME` | `Schule` | erscheint in der Oberfläche und im Word-Export |
| `BG_MODEL` | `gemma3:12b` | Sprachmodell in Ollama |
| `BG_EMBED_MODEL` | `bge-m3` | Modell für die semantische Suche; leer = Stichwortsuche |
| `BG_NUM_CTX` | `16384` | Kontextlänge (Tokens) |
| `BG_TEMPERATURE` | `0.4` | tiefer = nüchterner, höher = abwechslungsreicher |
| `BG_OLLAMA_URL` | `http://127.0.0.1:11434` | Adresse von Ollama |
| `BG_DATA_DIR` | `./data` | Speicherort der Datenbank |
| `BG_SESSION_HOURS` | `8` | automatische Abmeldung nach x Stunden |
| `BG_HTTPS_ONLY` | `0` | `1` hinter einem HTTPS-Proxy |
| `BG_MAX_UPLOAD_MB` | `25` | maximale Dateigrösse |

## 7. Entwicklung

```bash
pip install -r requirements.txt pytest
python -m pytest            # Tests laufen mit BG_LLM_BACKEND=mock, ohne Modell
BG_LLM_BACKEND=mock python -m uvicorn app.main:app --reload
```

Aufbau:

```
app/
  main.py        Webseiten und API
  prompts.py     Systemprompt, Standard-Berichtsarten, Überarbeitungsfunktionen
  retrieval.py   Auswahl relevanter Unterlagen (Embeddings bzw. Stichwortsuche)
  documents.py   Textextraktion (PDF/DOCX/RTF/TXT) und Aufteilung in Abschnitte
  llm.py         Anbindung an Ollama
  export.py      Word-Export
  auth.py        Passwörter, Sitzungen, Rechte
  db.py          SQLite-Schema
  cli.py         Kommandozeile (Benutzer, Backup)
```
