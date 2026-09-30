"use strict";

const csrf = () => document.querySelector('meta[name="csrf"]').content;

// Bestätigungsdialoge (CSP erlaubt keine Inline-Skripte)
document.addEventListener("submit", (e) => {
  const msg = e.target.dataset.confirm;
  if (msg && !confirm(msg)) e.preventDefault();
});
document.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-confirm]");
  if (btn && !confirm(btn.dataset.confirm)) e.preventDefault();
});

let controller = null;

async function streamInto(url, body, target, statusEl) {
  controller = new AbortController();
  statusEl.textContent = "Das lokale Modell schreibt … (je nach Rechner 1–5 Minuten)";
  target.value = "";
  const started = Date.now();
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf() },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!res.ok) {
      let msg = res.statusText;
      try { msg = (await res.json()).error || msg; } catch (_) {}
      throw new Error(msg);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      target.value += decoder.decode(value, { stream: true });
      target.scrollTop = target.scrollHeight;
    }
    const secs = Math.round((Date.now() - started) / 1000);
    statusEl.textContent = `Fertig (${secs} s). Bitte Text sorgfältig prüfen und Platzhalter [Ergänzen: …] ausfüllen.`;
  } catch (err) {
    statusEl.textContent = err.name === "AbortError" ? "Abgebrochen." : "Fehler: " + err.message;
  } finally {
    controller = null;
  }
}

// ---- Seite «Bericht erstellen»
const genForm = document.getElementById("gen-form");
if (genForm) {
  const out = document.getElementById("output");
  const status = document.getElementById("gen-status");
  const genBtn = document.getElementById("gen-btn");
  const stopBtn = document.getElementById("stop-btn");
  const saveForm = document.getElementById("save-form");

  genForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (out.value.trim() && !confirm("Der aktuelle Entwurf wird ersetzt. Fortfahren?")) return;
    const fd = new FormData(genForm);
    const body = {
      student_id: Number(genForm.dataset.student),
      report_type_id: Number(fd.get("report_type_id")),
      period: fd.get("period") || "",
      observations: fd.get("observations") || "",
      extra: fd.get("extra") || "",
      document_ids: fd.getAll("document_ids").map(Number),
      use_kb: fd.get("use_kb") === "on",
    };
    genBtn.disabled = true;
    stopBtn.hidden = false;
    await streamInto("/api/generate", body, out, status);
    genBtn.disabled = false;
    stopBtn.hidden = true;
  });
  stopBtn.addEventListener("click", () => controller && controller.abort());

  saveForm.addEventListener("submit", () => {
    const fd = new FormData(genForm);
    for (const k of ["report_type_id", "period", "observations"]) {
      saveForm.elements[k].value = fd.get(k) || "";
    }
  });
}

// ---- Seite «Bericht bearbeiten»: Überarbeiten mit KI
const reviseOut = document.getElementById("revise-output");
if (reviseOut) {
  const editor = document.getElementById("output");
  const status = document.getElementById("gen-status");
  let range = null;

  document.querySelectorAll("button.revise").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const hasSel = editor.selectionEnd > editor.selectionStart;
      range = hasSel ? [editor.selectionStart, editor.selectionEnd] : [0, editor.value.length];
      const text = editor.value.slice(range[0], range[1]);
      const instruction = document.getElementById("revise-instruction").value;
      if (!btn.dataset.action && !instruction.trim()) {
        status.textContent = "Bitte eine eigene Anweisung eingeben.";
        return;
      }
      document.querySelectorAll("button.revise").forEach((b) => (b.disabled = true));
      await streamInto("/api/revise", { text, action: btn.dataset.action, instruction }, reviseOut, status);
      document.querySelectorAll("button.revise").forEach((b) => (b.disabled = false));
    });
  });

  document.getElementById("revise-apply").addEventListener("click", () => {
    if (!range || !reviseOut.value.trim()) return;
    editor.value = editor.value.slice(0, range[0]) + reviseOut.value + editor.value.slice(range[1]);
    reviseOut.value = "";
    range = null;
    status.textContent = "Übernommen – bitte speichern nicht vergessen.";
  });
}

// Warnung bei ungespeicherten Änderungen
const reportForm = document.getElementById("report-form") || document.getElementById("save-form");
if (reportForm) {
  let dirty = false;
  const editor = document.getElementById("output");
  const initial = editor.value;
  const check = () => (dirty = editor.value !== initial);
  editor.addEventListener("input", check);
  setInterval(check, 2000);
  reportForm.addEventListener("submit", () => (dirty = false));
  window.addEventListener("beforeunload", (e) => {
    if (dirty) { e.preventDefault(); e.returnValue = ""; }
  });
}
