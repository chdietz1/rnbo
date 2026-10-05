# Live MIDI – Smartphones als Controller für Ableton Live

Zwei Personen steuern Ableton Live mit dem Smartphone:

```
Smartphone A ─┐                         ┌─ MIDI-Kanal 1 (Person A)
              ├─ WLAN ─► Server ─► Browser (Host-Seite) ─► IAC-Bus ─► Ableton Live
Smartphone B ─┘                         └─ MIDI-Kanal 2 (Person B)
```

- Auf dem Bildschirm ist ein QR-Code. Wer zuerst scannt, wird **Person A**, die nächste Person **Person B**.
- Jede Person bekommt eigene farbige Buttons.
- Person A sendet auf **MIDI-Kanal 1**, Person B auf **MIDI-Kanal 2**.
- Jeder Button sendet eine eigene Note: Note On beim Drücken, Note Off beim Loslassen.
  Voreinstellung: Button 1–6 = Note 36–41 (C1–F1).
- Wer die Seite neu lädt, behält die eigene Rolle.
- Wenn ein Handy die Verbindung verliert, werden seine Noten automatisch beendet.
- Auf der Host-Seite lässt sich jede Rolle zurücksetzen, damit eine andere Person sie übernehmen kann.

## Starten

```sh
cd live-midi
npm install      # nur beim ersten Mal
npm start
```

Danach **auf dem Rechner in Chrome oder Edge** `http://localhost:3000` öffnen und den MIDI-Zugriff erlauben.
Wichtig: über `localhost`, nicht über die IP-Adresse, sonst sperrt der Browser MIDI.
Als Ausgang wird automatisch der IAC-Bus gewählt, falls vorhanden.

Die Smartphones müssen im **selben WLAN** sein wie der Rechner.

## Ableton Live einrichten

1. macOS: Im Programm „Audio-MIDI-Setup“ das MIDI-Studio öffnen, den **IAC-Treiber**
   doppelklicken und „Gerät ist online“ anhaken.
2. In Live unter Einstellungen → Link, Tempo & MIDI beim Eingang **IAC-Treiber (Bus 1)** die Option **Spur** einschalten.
3. Zwei MIDI-Spuren anlegen:
   - Spur „Midi A“: MIDI From = IAC-Treiber (Bus 1), Kanal = **Ch. 1**
   - Spur „Midi B“: MIDI From = IAC-Treiber (Bus 1), Kanal = **Ch. 2**
4. Die Spuren scharf schalten oder Monitor auf „In“ stellen.

## Anpassen

Anzahl, Farben, Beschriftung und Noten der Buttons sowie die MIDI-Kanäle stehen in
`public/config.js`.

## Wenn etwas nicht klappt

- **Das Handy lädt die Seite nicht:** Die macOS-Firewall muss eingehende Verbindungen für `node` erlauben.
  Gäste-WLANs blockieren oft Verbindungen zwischen den Geräten.
- **Die IP im QR-Code ist falsch** (z. B. bei mehreren Netzwerkadaptern): Mit
  `HOST_IP=192.168.1.20 npm start` die richtige Adresse vorgeben.
- **Ein anderer Port wird gebraucht:** `PORT=8080 npm start`
