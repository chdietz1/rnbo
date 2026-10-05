// Gemeinsame Einstellungen für Host- und Smartphone-Seite.
//
// Jede Person sendet auf einem eigenen MIDI-Kanal, so lassen sich in Ableton
// zwei MIDI-Spuren anlegen, die nur "Midi A" bzw. "Midi B" empfangen.
// Jeder Button sendet eine eigene Note (Note On beim Drücken, Note Off beim Loslassen).

window.LIVE_MIDI_CONFIG = {
    persons: {
        A: {
            midiChannel: 1, // 1-16
            buttons: [
                { label: "1", color: "#e63946", note: 36 },
                { label: "2", color: "#f4a261", note: 37 },
                { label: "3", color: "#e9c46a", note: 38 },
                { label: "4", color: "#ff006e", note: 39 },
                { label: "5", color: "#fb5607", note: 40 },
                { label: "6", color: "#ffbe0b", note: 41 },
            ],
        },
        B: {
            midiChannel: 2,
            buttons: [
                { label: "1", color: "#3a86ff", note: 36 },
                { label: "2", color: "#2a9d8f", note: 37 },
                { label: "3", color: "#8338ec", note: 38 },
                { label: "4", color: "#06d6a0", note: 39 },
                { label: "5", color: "#118ab2", note: 40 },
                { label: "6", color: "#7209b7", note: 41 },
            ],
        },
    },
    velocity: 100,
};
