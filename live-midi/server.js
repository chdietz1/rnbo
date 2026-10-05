// Kleiner Server für das Smartphone → Browser → MIDI → Ableton Live Setup.
//
// - Liefert die Host-Seite (http://localhost:PORT) und die Smartphone-Seite (/p) aus
// - Vergibt die Rollen: erstes Smartphone = Person A, zweites = Person B
// - Leitet Button-Events der Smartphones per WebSocket an die Host-Seite weiter;
//   die Host-Seite macht daraus MIDI und schickt es an den IAC-Bus

const http = require("http");
const fs = require("fs");
const path = require("path");
const os = require("os");
const QRCode = require("qrcode");
const { WebSocketServer } = require("ws");

const PORT = Number(process.env.PORT) || 3000;
const PUBLIC_DIR = path.join(__dirname, "public");
const SLOTS = ["A", "B"];

function lanAddress() {
    if (process.env.HOST_IP) return process.env.HOST_IP;
    for (const addrs of Object.values(os.networkInterfaces())) {
        for (const a of addrs || []) {
            if (a.family === "IPv4" && !a.internal) return a.address;
        }
    }
    return "localhost";
}

const PHONE_URL = `http://${lanAddress()}:${PORT}/p`;

const MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
};

const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, "http://x");

    if (url.pathname === "/qr.svg") {
        const svg = await QRCode.toString(PHONE_URL, { type: "svg", margin: 1 });
        res.writeHead(200, { "Content-Type": MIME[".svg"], "Cache-Control": "no-store" });
        return res.end(svg);
    }
    if (url.pathname === "/info") {
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(JSON.stringify({ phoneUrl: PHONE_URL }));
    }

    const file = url.pathname === "/" ? "host.html"
        : url.pathname === "/p" ? "phone.html"
        : url.pathname.slice(1);
    const filePath = path.join(PUBLIC_DIR, path.normalize(file));
    if (!filePath.startsWith(PUBLIC_DIR)) {
        res.writeHead(403);
        return res.end();
    }
    fs.readFile(filePath, (err, data) => {
        if (err) {
            res.writeHead(404);
            return res.end("Not found");
        }
        res.writeHead(200, { "Content-Type": MIME[path.extname(filePath)] || "application/octet-stream" });
        res.end(data);
    });
});

// --- Rollenverwaltung ---------------------------------------------------------

// slot -> { clientId, socket | null }
const slots = Object.fromEntries(SLOTS.map(s => [s, null]));
const hosts = new Set();

function send(ws, msg) {
    if (ws && ws.readyState === ws.OPEN) ws.send(JSON.stringify(msg));
}

function toHosts(msg) {
    for (const h of hosts) send(h, msg);
}

function status() {
    return {
        type: "status",
        slots: Object.fromEntries(SLOTS.map(s => [s, slots[s]
            ? { taken: true, connected: !!slots[s].socket }
            : { taken: false, connected: false }])),
    };
}

function assignSlot(clientId) {
    const existing = SLOTS.find(s => slots[s] && slots[s].clientId === clientId);
    if (existing) return existing;
    const free = SLOTS.find(s => !slots[s]);
    if (free) slots[free] = { clientId, socket: null };
    return free || null;
}

function releaseSlot(slot) {
    const entry = slots[slot];
    if (!entry) return;
    slots[slot] = null;
    send(entry.socket, { type: "released" });
    toHosts({ type: "allOff", person: slot });
}

const wss = new WebSocketServer({ server, path: "/ws" });

wss.on("connection", ws => {
    let role = null;   // "host" | "phone"
    let slot = null;   // "A" | "B" bei Smartphones

    ws.on("message", raw => {
        let msg;
        try { msg = JSON.parse(raw); } catch { return; }

        if (msg.type === "hello" && msg.role === "host") {
            role = "host";
            hosts.add(ws);
            send(ws, status());
            return;
        }

        if (msg.type === "hello" && msg.role === "phone" && typeof msg.clientId === "string") {
            role = "phone";
            slot = assignSlot(msg.clientId);
            if (!slot) return send(ws, { type: "full" });
            // Gleiche Person in neuem Tab: alte Verbindung ablösen
            const previous = slots[slot].socket;
            if (previous && previous !== ws) previous.close();
            slots[slot].socket = ws;
            send(ws, { type: "role", person: slot });
            toHosts(status());
            return;
        }

        if (role === "phone" && slot && slots[slot] && slots[slot].socket === ws && msg.type === "btn") {
            const button = Number(msg.button);
            if (!Number.isInteger(button) || button < 0 || button > 127) return;
            if (msg.state !== "down" && msg.state !== "up") return;
            toHosts({ type: "btn", person: slot, button, state: msg.state });
            return;
        }

        if (role === "host" && msg.type === "reset") {
            const targets = msg.person ? [msg.person] : SLOTS;
            targets.filter(s => SLOTS.includes(s)).forEach(releaseSlot);
            toHosts(status());
        }
    });

    ws.on("close", () => {
        if (role === "host") hosts.delete(ws);
        if (role === "phone" && slot && slots[slot] && slots[slot].socket === ws) {
            slots[slot].socket = null;
            // Hängende Noten vermeiden, wenn das Handy die Verbindung verliert
            toHosts({ type: "allOff", person: slot });
            toHosts(status());
        }
    });
});

server.listen(PORT, () => {
    console.log("");
    console.log(`  Host-Seite (auf diesem Rechner in Chrome öffnen):  http://localhost:${PORT}`);
    console.log(`  Smartphone-Seite (über QR-Code):                   ${PHONE_URL}`);
    console.log("");
});
