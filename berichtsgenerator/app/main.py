"""Berichtsgenerator – lokale Webanwendung zum Verfassen formativer Berichte."""
from __future__ import annotations

import json
import re
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import auth, config, db, documents, importer, llm, prompts, retrieval
from .auth import LoginRequired, check_csrf, require_admin, require_user
from .export import report_to_docx

APP_DIR = Path(__file__).resolve().parent

@asynccontextmanager
async def lifespan(_app):
    db.init_db()
    yield


app = FastAPI(title="Berichtsgenerator", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=config.SECRET_KEY,
    session_cookie="bg_session",
    max_age=config.SESSION_MAX_AGE,
    same_site="strict",
    https_only=config.HTTPS_ONLY,
)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")
templates.env.globals["school_name"] = config.SCHOOL_NAME

DOC_TYPES = [
    "Beurteilungsbericht",
    "Standortbericht",
    "Förderplan",
    "Protokoll Standortgespräch",
    "Lernbericht",
    "Abklärungsbericht / Fachbericht",
    "Beobachtungsnotizen",
    "Anderes",
]
KB_TYPES = ["Kantonale Vorgabe", "Leitfaden", "Lehrplan", "Schulinternes Konzept", "Musterbericht",
            documents.TEMPLATE_TYPE, "Anderes"]


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        "connect-src 'self'; frame-ancestors 'none'; form-action 'self'"
    )
    return response


@app.exception_handler(LoginRequired)
async def _login_required(request: Request, exc: LoginRequired):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": "Nicht angemeldet."}, status_code=401)
    return RedirectResponse("/login", status_code=303)


@app.exception_handler(HTTPException)
async def _http_error(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)
    return render(request, "error.html", {"message": exc.detail}, status_code=exc.status_code)


def render(request: Request, name: str, ctx: dict | None = None, status_code: int = 200):
    ctx = dict(ctx or {})
    ctx.setdefault("user", auth.current_user(request))
    ctx["csrf"] = auth.csrf_token(request)
    ctx["flash"] = request.session.pop("flash", None)
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


def redirect(url: str, flash: str | None = None, request: Request | None = None):
    if flash and request is not None:
        request.session["flash"] = flash
    return RedirectResponse(url, status_code=303)


async def form_data(request: Request) -> dict:
    form = await request.form()
    check_csrf(request, form.get("csrf"))
    return form


# --------------------------------------------------------------------------- Anmeldung


def _has_users() -> bool:
    with db.get_conn() as conn:
        return conn.execute("SELECT 1 FROM users LIMIT 1").fetchone() is not None


@app.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request):
    if _has_users():
        return redirect("/login")
    return render(request, "setup.html")


@app.post("/setup")
async def setup_submit(request: Request):
    if _has_users():
        return redirect("/login")
    form = await form_data(request)
    username, display = form.get("username", "").strip(), form.get("display_name", "").strip()
    password = form.get("password", "")
    error = auth.validate_new_password(password)
    if not username or not display:
        error = "Bitte alle Felder ausfüllen."
    if password != form.get("password2"):
        error = "Die Passwörter stimmen nicht überein."
    if error:
        return render(request, "setup.html", {"error": error})
    with db.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, display_name, pw_hash, is_admin, created_at) VALUES (?, ?, ?, 1, ?)",
            (username, display, auth.hash_password(password), db.now()),
        )
        user = {"id": cur.lastrowid, "username": username}
        db.audit(conn, user, "setup", "Erste Administratorin/erster Administrator erstellt")
    request.session.clear()
    request.session["uid"] = user["id"]
    return redirect("/", "Willkommen! Das System ist eingerichtet.", request)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if not _has_users():
        return redirect("/setup")
    return render(request, "login.html", {"user": None})


@app.post("/login")
async def login_submit(request: Request):
    form = await form_data(request)
    username = form.get("username", "").strip()
    key = f"{request.client.host if request.client else '-'}:{username.lower()}"
    if auth.too_many_attempts(key):
        return render(request, "login.html", {"user": None, "error": "Zu viele Fehlversuche. Bitte 15 Minuten warten."})
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ? AND active = 1", (username,)).fetchone()
        if not row or not auth.verify_password(form.get("password", ""), row["pw_hash"]):
            auth.register_failure(key)
            db.audit(conn, None, "login_fehlgeschlagen", username)
            return render(request, "login.html", {"user": None, "error": "Benutzername oder Passwort falsch."})
        db.audit(conn, dict(row), "login")
    auth.clear_failures(key)
    request.session.clear()
    request.session["uid"] = row["id"]
    return redirect("/")


@app.post("/logout")
async def logout(request: Request):
    await form_data(request)
    request.session.clear()
    return redirect("/login")


@app.get("/account", response_class=HTMLResponse)
def account_page(request: Request):
    require_user(request)
    return render(request, "account.html")


@app.post("/account/password")
async def account_password(request: Request):
    user = require_user(request)
    form = await form_data(request)
    if not auth.verify_password(form.get("old", ""), user["pw_hash"]):
        return render(request, "account.html", {"error": "Das bisherige Passwort ist falsch."})
    error = auth.validate_new_password(form.get("new", ""))
    if form.get("new") != form.get("new2"):
        error = "Die neuen Passwörter stimmen nicht überein."
    if error:
        return render(request, "account.html", {"error": error})
    with db.get_conn() as conn:
        conn.execute("UPDATE users SET pw_hash = ? WHERE id = ?", (auth.hash_password(form["new"]), user["id"]))
        db.audit(conn, user, "passwort_geaendert")
    return redirect("/account", "Passwort geändert.", request)


# --------------------------------------------------------------------------- Übersicht


def _visible_students(conn, user):
    if user["is_admin"]:
        sql = "SELECT s.* FROM students s"
        args: tuple = ()
    else:
        sql = "SELECT s.* FROM students s JOIN student_users su ON su.student_id = s.id WHERE su.user_id = ?"
        args = (user["id"],)
    return conn.execute(sql + " ORDER BY s.last_name, s.first_name", args).fetchall()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    user = require_user(request)
    with db.get_conn() as conn:
        students = _visible_students(conn, user)
        ids = [s["id"] for s in students] or [0]
        marks = ",".join("?" * len(ids))
        reports = conn.execute(
            f"SELECT r.*, s.first_name, s.last_name FROM reports r JOIN students s ON s.id = r.student_id "
            f"WHERE r.student_id IN ({marks}) ORDER BY r.updated_at DESC LIMIT 15",
            ids,
        ).fetchall()
    return render(request, "dashboard.html", {"students": students, "reports": reports, "status": llm.status()})


@app.get("/api/status")
def api_status(request: Request):
    require_user(request)
    return llm.status()


# --------------------------------------------------------------------------- Schülerinnen/Schüler


@app.get("/students", response_class=HTMLResponse)
def students_page(request: Request):
    user = require_user(request)
    with db.get_conn() as conn:
        students = _visible_students(conn, user)
    return render(request, "students.html", {"students": students})


@app.post("/students")
async def students_create(request: Request):
    user = require_user(request)
    form = await form_data(request)
    first, last = form.get("first_name", "").strip(), form.get("last_name", "").strip()
    if not first or not last:
        return redirect("/students", "Vor- und Nachname sind erforderlich.", request)
    with db.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO students (first_name, last_name, birth_year, class_name, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (first, last, form.get("birth_year", "").strip(), form.get("class_name", "").strip(),
             form.get("notes", "").strip(), db.now()),
        )
        sid = cur.lastrowid
        conn.execute("INSERT INTO student_users (student_id, user_id) VALUES (?, ?)", (sid, user["id"]))
        db.audit(conn, user, "schueler_erstellt", f"id={sid}")
    return redirect(f"/students/{sid}")


@app.get("/admin/import", response_class=HTMLResponse)
def import_page(request: Request):
    require_admin(request)
    return render(request, "import.html", {"columns": importer.COLUMNS})


@app.get("/admin/import/vorlage.csv")
def import_template(request: Request):
    require_admin(request)
    return Response(
        importer.TEMPLATE_CSV.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=Vorlage_Schuelerliste.csv"},
    )


@app.post("/admin/import")
async def import_submit(request: Request):
    admin = require_admin(request)
    form = await form_data(request)
    upload = form.get("file")
    if upload is None or not getattr(upload, "filename", ""):
        return render(request, "import.html", {"columns": importer.COLUMNS, "error": "Bitte eine Datei auswählen."})
    data = await upload.read()
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        return render(request, "import.html", {"columns": importer.COLUMNS, "error": "Die Datei ist zu gross."})
    try:
        students, errors = await run_in_threadpool(importer.parse_students, upload.filename, data)
    except importer.ImportError_ as e:
        return render(request, "import.html", {"columns": importer.COLUMNS, "error": str(e)})
    with db.get_conn() as conn:
        result = importer.import_students(conn, students, admin)
    result["messages"] = errors + result["messages"]
    return render(request, "import.html", {"columns": importer.COLUMNS, "result": result})


@app.get("/students/{sid}", response_class=HTMLResponse)
def student_page(request: Request, sid: int):
    user = require_user(request)
    with db.get_conn() as conn:
        student = auth.get_student_or_403(conn, user, sid)
        docs = conn.execute(
            "SELECT id, title, doc_type, doc_date, filename, template_id, length(content_text) AS size, created_at "
            "FROM documents WHERE student_id = ? ORDER BY COALESCE(doc_date, created_at) DESC",
            (sid,),
        ).fetchall()
        reports = conn.execute(
            "SELECT r.*, u.display_name AS author FROM reports r LEFT JOIN users u ON u.id = r.created_by "
            "WHERE r.student_id = ? ORDER BY r.updated_at DESC",
            (sid,),
        ).fetchall()
        members = conn.execute(
            "SELECT u.id, u.display_name, u.username FROM users u JOIN student_users su ON su.user_id = u.id "
            "WHERE su.student_id = ? ORDER BY u.display_name",
            (sid,),
        ).fetchall()
        all_users = conn.execute(
            "SELECT id, display_name, username FROM users WHERE active = 1 ORDER BY display_name"
        ).fetchall()
        templates = _templates(conn)
        db.audit(conn, user, "schueler_angesehen", f"id={sid}")
    return render(request, "student.html", {
        "student": student, "docs": docs, "reports": reports, "members": members,
        "all_users": all_users, "doc_types": DOC_TYPES, "templates": templates,
    })


@app.post("/students/{sid}/edit")
async def student_edit(request: Request, sid: int):
    user = require_user(request)
    form = await form_data(request)
    with db.get_conn() as conn:
        auth.get_student_or_403(conn, user, sid)
        conn.execute(
            "UPDATE students SET first_name = ?, last_name = ?, birth_year = ?, class_name = ?, notes = ? WHERE id = ?",
            (form.get("first_name", "").strip(), form.get("last_name", "").strip(), form.get("birth_year", "").strip(),
             form.get("class_name", "").strip(), form.get("notes", "").strip(), sid),
        )
        db.audit(conn, user, "schueler_bearbeitet", f"id={sid}")
    return redirect(f"/students/{sid}", "Gespeichert.", request)


@app.post("/students/{sid}/members")
async def student_members(request: Request, sid: int):
    user = require_user(request)
    form = await form_data(request)
    with db.get_conn() as conn:
        auth.get_student_or_403(conn, user, sid)
        target = int(form.get("user_id", 0))
        if form.get("action") == "remove":
            conn.execute("DELETE FROM student_users WHERE student_id = ? AND user_id = ?", (sid, target))
            db.audit(conn, user, "zugriff_entzogen", f"schueler={sid} user={target}")
        else:
            conn.execute("INSERT OR IGNORE INTO student_users (student_id, user_id) VALUES (?, ?)", (sid, target))
            db.audit(conn, user, "zugriff_erteilt", f"schueler={sid} user={target}")
    if target == user["id"] and form.get("action") == "remove" and not user["is_admin"]:
        return redirect("/students", "Sie haben keinen Zugriff mehr auf dieses Dossier.", request)
    return redirect(f"/students/{sid}", "Zugriffsrechte aktualisiert.", request)


@app.post("/students/{sid}/delete")
async def student_delete(request: Request, sid: int):
    user = require_admin(request)
    form = await form_data(request)
    with db.get_conn() as conn:
        student = auth.get_student_or_403(conn, user, sid)
        if form.get("confirm", "").strip() != student["last_name"]:
            return redirect(f"/students/{sid}", "Löschen abgebrochen: Nachname zur Bestätigung stimmt nicht.", request)
        conn.execute("DELETE FROM students WHERE id = ?", (sid,))
        db.audit(conn, user, "schueler_geloescht", f"id={sid}")
    return redirect("/students", "Dossier inkl. aller Dokumente und Berichte gelöscht.", request)


# --------------------------------------------------------------------------- Dokumente


async def _read_upload(form) -> tuple[str, str | None]:
    """Gibt (Text, Dateiname) zurück – aus Datei oder eingefügtem Text."""
    upload = form.get("file")
    if upload is not None and getattr(upload, "filename", ""):
        data = await upload.read()
        if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
            raise documents.ExtractionError(f"Datei ist grösser als {config.MAX_UPLOAD_MB} MB.")
        return await run_in_threadpool(documents.extract_text, upload.filename, data), upload.filename
    text = documents.normalize(form.get("text", ""))
    if not text:
        raise documents.ExtractionError("Bitte eine Datei auswählen oder Text einfügen.")
    return text, None


def _templates(conn) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT id, title, content_text FROM documents WHERE student_id IS NULL AND doc_type = ? ORDER BY title",
        (documents.TEMPLATE_TYPE,),
    )]


async def _save_document(request: Request, user, student_id: int | None, form) -> tuple[int, str, str]:
    """Speichert ein Dokument. Gibt (ID, Titel, Hinweis zum Vorlagen-Abgleich) zurück."""
    text, filename = await _read_upload(form)
    title = form.get("title", "").strip() or (filename or "Eingefügter Text")
    doc_type, doc_date = form.get("doc_type", "Anderes"), form.get("doc_date", "").strip() or None
    choice = form.get("template", "auto")

    def work() -> tuple[int, str]:  # im Threadpool, da die Embedding-Berechnung dauern kann
        with db.get_conn() as conn:
            content, template, note = text, None, ""
            if student_id is not None:
                content, template = documents.apply_template(text, _templates(conn), choice)
                if template:
                    note = f" Abgleich mit Vorlage «{template['title']}»: nur ausgefüllte Teile übernommen."
                    if not content:
                        content = "(Keine ausgefüllten Inhalte gegenüber der Vorlage gefunden.)"
                        note += " Achtung: Es wurde nichts Ausgefülltes gefunden."
            cur = conn.execute(
                "INSERT INTO documents (student_id, title, doc_type, doc_date, filename, content_text, full_text, "
                "template_id, uploaded_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (student_id, title, doc_type, doc_date, filename, content, text if template else None,
                 template["id"] if template else None, user["id"], db.now()),
            )
            if doc_type != documents.TEMPLATE_TYPE:
                documents.index_document(conn, cur.lastrowid, content)
            db.audit(conn, user, "dokument_hochgeladen", f"id={cur.lastrowid} schueler={student_id}")
            return cur.lastrowid, note

    did, note = await run_in_threadpool(work)
    return did, title, note


@app.post("/students/{sid}/documents")
async def document_upload(request: Request, sid: int):
    user = require_user(request)
    form = await form_data(request)
    with db.get_conn() as conn:
        auth.get_student_or_403(conn, user, sid)
    try:
        _, title, note = await _save_document(request, user, sid, form)
    except documents.ExtractionError as e:
        return redirect(f"/students/{sid}", f"Fehler: {e}", request)
    return redirect(f"/students/{sid}", f"Dokument «{title}» gespeichert.{note}", request)


def _get_document(conn, user, did: int) -> dict:
    doc = conn.execute("SELECT * FROM documents WHERE id = ?", (did,)).fetchone()
    if not doc:
        raise HTTPException(404, "Dokument nicht gefunden.")
    if doc["student_id"] is not None:
        auth.get_student_or_403(conn, user, doc["student_id"])
    return dict(doc)


@app.get("/documents/{did}", response_class=HTMLResponse)
def document_view(request: Request, did: int):
    user = require_user(request)
    with db.get_conn() as conn:
        doc = _get_document(conn, user, did)
        templates = _templates(conn) if doc["student_id"] is not None else []
        used = next((t for t in templates if t["id"] == doc.get("template_id")), None)
        db.audit(conn, user, "dokument_angesehen", f"id={did}")
    return render(request, "document.html", {"doc": doc, "templates": templates, "used_template": used})


@app.post("/documents/{did}/template")
async def document_template(request: Request, did: int):
    user = require_user(request)
    form = await form_data(request)

    def work() -> str:
        with db.get_conn() as conn:
            doc = _get_document(conn, user, did)
            if doc["student_id"] is None:
                raise HTTPException(400, "Nur für Unterlagen in einem Dossier.")
            original = doc.get("full_text") or doc["content_text"]
            content, template = documents.apply_template(original, _templates(conn), form.get("template", "auto"))
            if template and not content:
                content = "(Keine ausgefüllten Inhalte gegenüber der Vorlage gefunden.)"
            conn.execute(
                "UPDATE documents SET content_text = ?, full_text = ?, template_id = ? WHERE id = ?",
                (content, original if template else None, template["id"] if template else None, did),
            )
            documents.index_document(conn, did, content)
            db.audit(conn, user, "dokument_abgeglichen", f"id={did}")
            if template:
                return f"Abgeglichen mit «{template['title']}»."
            return "Keine passende Vorlage gefunden. Der vollständige Text wird verwendet." \
                if form.get("template", "auto") == "auto" else "Vollständiger Text wird verwendet."

    msg = await run_in_threadpool(work)
    return redirect(f"/documents/{did}", msg, request)


@app.post("/documents/{did}/delete")
async def document_delete(request: Request, did: int):
    user = require_user(request)
    await form_data(request)
    with db.get_conn() as conn:
        doc = _get_document(conn, user, did)
        if doc["student_id"] is None and not user["is_admin"]:
            raise HTTPException(403, "Nur Administratorinnen/Administratoren können die Wissensbasis ändern.")
        conn.execute("DELETE FROM documents WHERE id = ?", (did,))
        db.audit(conn, user, "dokument_geloescht", f"id={did}")
    target = f"/students/{doc['student_id']}" if doc["student_id"] else "/knowledge"
    return redirect(target, "Dokument gelöscht.", request)


# --------------------------------------------------------------------------- Wissensbasis


@app.get("/knowledge", response_class=HTMLResponse)
def knowledge_page(request: Request):
    require_user(request)
    with db.get_conn() as conn:
        docs = conn.execute(
            "SELECT id, title, doc_type, doc_date, filename, length(content_text) AS size, created_at, "
            "(SELECT COUNT(*) FROM chunks c WHERE c.document_id = d.id AND c.embedding IS NOT NULL) AS emb "
            "FROM documents d WHERE student_id IS NULL ORDER BY doc_type, title"
        ).fetchall()
    return render(request, "knowledge.html", {"docs": docs, "kb_types": KB_TYPES})


@app.post("/knowledge")
async def knowledge_upload(request: Request):
    user = require_admin(request)
    form = await form_data(request)
    try:
        _, title, _note = await _save_document(request, user, None, form)
    except documents.ExtractionError as e:
        return redirect("/knowledge", f"Fehler: {e}", request)
    return redirect("/knowledge", f"«{title}» zur Wissensbasis hinzugefügt.", request)


@app.post("/knowledge/reindex")
async def knowledge_reindex(request: Request):
    user = require_admin(request)
    await form_data(request)

    def work():
        with db.get_conn() as conn:
            for d in conn.execute("SELECT id, content_text FROM documents").fetchall():
                documents.index_document(conn, d["id"], d["content_text"])
            db.audit(conn, user, "neu_indexiert")

    await run_in_threadpool(work)
    return redirect("/knowledge", "Alle Dokumente wurden neu indexiert.", request)


# --------------------------------------------------------------------------- Berichte erstellen


def _report_types(conn, only_active=True):
    sql = "SELECT * FROM report_types" + (" WHERE active = 1" if only_active else "") + " ORDER BY sort, name"
    return conn.execute(sql).fetchall()


@app.get("/students/{sid}/generate", response_class=HTMLResponse)
def generate_page(request: Request, sid: int):
    user = require_user(request)
    with db.get_conn() as conn:
        student = auth.get_student_or_403(conn, user, sid)
        docs = conn.execute(
            "SELECT id, title, doc_type, doc_date FROM documents WHERE student_id = ? "
            "ORDER BY COALESCE(doc_date, created_at) DESC",
            (sid,),
        ).fetchall()
        types = _report_types(conn)
        skills = _skills(conn, user)
    return render(request, "generate.html", {"student": student, "docs": docs, "types": types, "skills": skills})


async def _json_body(request: Request) -> dict:
    check_csrf(request, request.headers.get("X-CSRF-Token"))
    try:
        return await request.json()
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(400, "Ungültige Anfrage.")


def _stream(messages: list[dict]) -> StreamingResponse:
    async def gen():
        try:
            async for piece in llm.chat_stream(messages):
                yield piece
        except llm.LLMError as e:
            yield f"\n\n[FEHLER: {e}]"

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8",
                             headers={"X-Accel-Buffering": "no"})


@app.post("/api/generate")
async def api_generate(request: Request):
    user = require_user(request)
    body = await _json_body(request)
    sid = int(body.get("student_id", 0))
    doc_ids = [int(x) for x in body.get("document_ids", [])]

    def prepare():
        with db.get_conn() as conn:
            student = auth.get_student_or_403(conn, user, sid)
            rt = conn.execute("SELECT * FROM report_types WHERE id = ?", (int(body.get("report_type_id", 0)),)).fetchone()
            if not rt:
                raise HTTPException(400, "Unbekannte Berichtsart.")
            if doc_ids:  # nur Dokumente dieses Kindes zulassen
                marks = ",".join("?" * len(doc_ids))
                allowed = {r["id"] for r in conn.execute(
                    f"SELECT id FROM documents WHERE student_id = ? AND id IN ({marks})", [sid, *doc_ids])}
            else:
                allowed = set()
            query = f"{rt['name']}\n{rt['instructions']}\n{body.get('observations', '')}\n{body.get('extra', '')}"
            s_budget, kb_budget = retrieval.budgets()
            student_ctx = retrieval.build_student_context(conn, sorted(allowed), query, s_budget)
            kb_ctx = retrieval.build_kb_context(conn, query, kb_budget) if body.get("use_kb", True) else ""
            db.audit(conn, user, "bericht_generiert", f"schueler={sid} art={rt['key']} dokumente={len(allowed)}")
            return prompts.build_generation_messages(
                report_type=dict(rt), student=student, period=str(body.get("period", "")),
                observations=str(body.get("observations", "")), extra=str(body.get("extra", "")),
                student_context=student_ctx, kb_context=kb_ctx,
            )

    messages = await run_in_threadpool(prepare)
    return _stream(messages)


@app.post("/api/revise")
async def api_revise(request: Request):
    user = require_user(request)
    body = await _json_body(request)
    text = str(body.get("text", "")).strip()
    if not text:
        raise HTTPException(400, "Kein Text zum Überarbeiten.")
    action = str(body.get("action", ""))
    instruction = prompts.REVISE_ACTIONS.get(action) or str(body.get("instruction", "")).strip()
    if not instruction:
        raise HTTPException(400, "Keine Anweisung angegeben.")
    with db.get_conn() as conn:
        db.audit(conn, user, "text_ueberarbeitet", action or "eigene Anweisung")
    return _stream(prompts.build_revise_messages(text, instruction))


@app.post("/students/{sid}/reports")
async def report_create(request: Request, sid: int):
    user = require_user(request)
    form = await form_data(request)
    content = form.get("content", "").strip()
    if not content:
        return redirect(f"/students/{sid}/generate", "Der Bericht ist leer.", request)
    with db.get_conn() as conn:
        auth.get_student_or_403(conn, user, sid)
        rt_id = int(form.get("report_type_id") or 0) or None
        rt = conn.execute("SELECT name FROM report_types WHERE id = ?", (rt_id,)).fetchone() if rt_id else None
        title = form.get("title", "").strip() or (rt["name"] if rt else "Bericht")
        cur = conn.execute(
            "INSERT INTO reports (student_id, report_type_id, title, period, observations, content, status, "
            "created_by, updated_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'entwurf', ?, ?, ?, ?)",
            (sid, rt_id, title, form.get("period", "").strip(), form.get("observations", ""), content,
             user["id"], user["id"], db.now(), db.now()),
        )
        db.audit(conn, user, "bericht_gespeichert", f"id={cur.lastrowid}")
    return redirect(f"/reports/{cur.lastrowid}", "Entwurf gespeichert.", request)


def _get_report(conn, user, rid: int) -> tuple[dict, dict]:
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (rid,)).fetchone()
    if not row:
        raise HTTPException(404, "Bericht nicht gefunden.")
    student = auth.get_student_or_403(conn, user, row["student_id"])
    return dict(row), student


@app.get("/reports/{rid}", response_class=HTMLResponse)
def report_page(request: Request, rid: int):
    user = require_user(request)
    with db.get_conn() as conn:
        report, student = _get_report(conn, user, rid)
        authors = conn.execute(
            "SELECT (SELECT display_name FROM users WHERE id = ?) AS created, "
            "(SELECT display_name FROM users WHERE id = ?) AS updated",
            (report["created_by"], report["updated_by"]),
        ).fetchone()
        skills = _skills(conn, user)
    return render(request, "report.html", {
        "report": report, "student": student, "authors": authors, "skills": skills,
        "revise_actions": prompts.REVISE_ACTIONS,
    })


@app.post("/reports/{rid}")
async def report_save(request: Request, rid: int):
    user = require_user(request)
    form = await form_data(request)
    with db.get_conn() as conn:
        report, _ = _get_report(conn, user, rid)
        conn.execute(
            "UPDATE reports SET title = ?, period = ?, content = ?, updated_by = ?, updated_at = ? WHERE id = ?",
            (form.get("title", report["title"]).strip(), form.get("period", "").strip(),
             form.get("content", report["content"]), user["id"], db.now(), rid),
        )
        msg = "Gespeichert."
        if form.get("finalize") == "1" and report["status"] != "final":
            conn.execute("UPDATE reports SET status = 'final' WHERE id = ?", (rid,))
            # Finalisierte Berichte stehen künftig als Grundlage zur Verfügung
            text = form.get("content", report["content"])
            cur = conn.execute(
                "INSERT INTO documents (student_id, title, doc_type, doc_date, filename, content_text, uploaded_by, created_at) "
                "VALUES (?, ?, ?, ?, NULL, ?, ?, ?)",
                (report["student_id"], form.get("title", report["title"]).strip(), "Beurteilungsbericht",
                 form.get("period", "").strip() or db.now()[:10], text, user["id"], db.now()),
            )
            documents.index_document(conn, cur.lastrowid, text)
            msg = "Bericht finalisiert und als Grundlage für künftige Berichte abgelegt."
        db.audit(conn, user, "bericht_bearbeitet", f"id={rid}")
    return redirect(f"/reports/{rid}", msg, request)


@app.post("/reports/{rid}/delete")
async def report_delete(request: Request, rid: int):
    user = require_user(request)
    await form_data(request)
    with db.get_conn() as conn:
        report, _ = _get_report(conn, user, rid)
        conn.execute("DELETE FROM reports WHERE id = ?", (rid,))
        db.audit(conn, user, "bericht_geloescht", f"id={rid}")
    return redirect(f"/students/{report['student_id']}", "Bericht gelöscht.", request)


@app.get("/reports/{rid}/docx")
def report_docx(request: Request, rid: int):
    user = require_user(request)
    with db.get_conn() as conn:
        report, student = _get_report(conn, user, rid)
        author = conn.execute("SELECT display_name FROM users WHERE id = ?", (report["created_by"],)).fetchone()
        db.audit(conn, user, "bericht_exportiert", f"id={rid}")
    data = report_to_docx(report, student, author["display_name"] if author else user["display_name"], config.SCHOOL_NAME)
    name = re.sub(r"[^\w\- ]", "", f"{report['title']} {student['last_name']} {student['first_name']}").strip() + ".docx"
    return Response(
        data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"},
    )


# --------------------------------------------------------------------------- Skills (gespeicherte Anweisungen)


def _skills(conn, user) -> list[dict]:
    rows = conn.execute(
        "SELECT s.*, u.display_name AS owner FROM skills s LEFT JOIN users u ON u.id = s.owner_id "
        "WHERE s.owner_id = ? OR s.shared = 1 ORDER BY s.name COLLATE NOCASE",
        (user["id"],),
    ).fetchall()
    return [dict(r, own=r["owner_id"] == user["id"]) for r in rows]


def _can_edit_skill(conn, user, skill_id: int) -> dict:
    row = conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
    if not row or (row["owner_id"] != user["id"] and not user["is_admin"]):
        raise HTTPException(404, "Skill nicht gefunden oder keine Berechtigung.")
    return dict(row)


@app.get("/skills", response_class=HTMLResponse)
def skills_page(request: Request):
    user = require_user(request)
    with db.get_conn() as conn:
        skills = _skills(conn, user)
    return render(request, "skills.html", {"skills": skills})


@app.post("/skills")
async def skills_save(request: Request):
    user = require_user(request)
    form = await form_data(request)
    sid = int(form.get("id") or 0)
    with db.get_conn() as conn:
        if form.get("action") == "delete" and sid:
            skill = _can_edit_skill(conn, user, sid)
            conn.execute("DELETE FROM skills WHERE id = ?", (sid,))
            return redirect("/skills", f"Skill «{skill['name']}» gelöscht.", request)
        name, text = form.get("name", "").strip(), form.get("text", "").strip()
        if not name or not text:
            return redirect("/skills", "Name und Anweisung sind erforderlich.", request)
        shared = 1 if form.get("shared") else 0
        if sid:
            _can_edit_skill(conn, user, sid)
            conn.execute("UPDATE skills SET name = ?, text = ?, shared = ? WHERE id = ?", (name, text, shared, sid))
        else:
            conn.execute(
                "INSERT INTO skills (owner_id, name, text, shared, created_at) VALUES (?, ?, ?, ?, ?)",
                (user["id"], name, text, shared, db.now()),
            )
    return redirect("/skills", f"Skill «{name}» gespeichert.", request)


@app.post("/api/skills")
async def api_skill_create(request: Request):
    user = require_user(request)
    body = await _json_body(request)
    name, text = str(body.get("name", "")).strip(), str(body.get("text", "")).strip()
    if not name or not text:
        raise HTTPException(400, "Name und Anweisung sind erforderlich.")
    with db.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO skills (owner_id, name, text, shared, created_at) VALUES (?, ?, ?, ?, ?)",
            (user["id"], name, text, 1 if body.get("shared") else 0, db.now()),
        )
    return {"id": cur.lastrowid, "name": name, "text": text}


# --------------------------------------------------------------------------- Verwaltung


@app.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request):
    require_admin(request)
    with db.get_conn() as conn:
        users = conn.execute("SELECT * FROM users ORDER BY display_name").fetchall()
    return render(request, "admin_users.html", {"users": users})


@app.post("/admin/users")
async def admin_user_create(request: Request):
    admin = require_admin(request)
    form = await form_data(request)
    username, display = form.get("username", "").strip(), form.get("display_name", "").strip()
    error = auth.validate_new_password(form.get("password", ""))
    if not username or not display:
        error = "Benutzername und Name sind erforderlich."
    if error:
        return redirect("/admin/users", error, request)
    with db.get_conn() as conn:
        if conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
            return redirect("/admin/users", "Benutzername existiert bereits.", request)
        conn.execute(
            "INSERT INTO users (username, display_name, pw_hash, is_admin, created_at) VALUES (?, ?, ?, ?, ?)",
            (username, display, auth.hash_password(form["password"]), 1 if form.get("is_admin") else 0, db.now()),
        )
        db.audit(conn, admin, "benutzer_erstellt", username)
    return redirect("/admin/users", f"Benutzer «{username}» erstellt.", request)


@app.post("/admin/users/{uid}")
async def admin_user_update(request: Request, uid: int):
    admin = require_admin(request)
    form = await form_data(request)
    action = form.get("action")
    with db.get_conn() as conn:
        target = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        if not target:
            raise HTTPException(404, "Benutzer nicht gefunden.")
        if uid == admin["id"] and action in ("deactivate", "revoke_admin"):
            return redirect("/admin/users", "Sie können sich nicht selbst sperren oder die Adminrechte entziehen.", request)
        if action == "reset_password":
            error = auth.validate_new_password(form.get("password", ""))
            if error:
                return redirect("/admin/users", error, request)
            conn.execute("UPDATE users SET pw_hash = ? WHERE id = ?", (auth.hash_password(form["password"]), uid))
        elif action in ("activate", "deactivate"):
            conn.execute("UPDATE users SET active = ? WHERE id = ?", (1 if action == "activate" else 0, uid))
        elif action in ("grant_admin", "revoke_admin"):
            conn.execute("UPDATE users SET is_admin = ? WHERE id = ?", (1 if action == "grant_admin" else 0, uid))
        else:
            raise HTTPException(400, "Unbekannte Aktion.")
        db.audit(conn, admin, f"benutzer_{action}", target["username"])
    return redirect("/admin/users", "Gespeichert.", request)


@app.get("/admin/report-types", response_class=HTMLResponse)
def admin_report_types(request: Request):
    require_admin(request)
    with db.get_conn() as conn:
        types = _report_types(conn, only_active=False)
    return render(request, "admin_report_types.html", {"types": types, "system_prompt": prompts.SYSTEM_PROMPT})


@app.post("/admin/report-types")
async def admin_report_type_save(request: Request):
    admin = require_admin(request)
    form = await form_data(request)
    name, instructions = form.get("name", "").strip(), form.get("instructions", "").strip()
    if not name or not instructions:
        return redirect("/admin/report-types", "Name und Anweisungen sind erforderlich.", request)
    rid = int(form.get("id") or 0)
    with db.get_conn() as conn:
        if form.get("action") == "delete" and rid:
            conn.execute("DELETE FROM report_types WHERE id = ?", (rid,))
            msg = "Berichtsart gelöscht."
        elif rid:
            conn.execute(
                "UPDATE report_types SET name = ?, description = ?, instructions = ?, active = ?, sort = ? WHERE id = ?",
                (name, form.get("description", "").strip(), instructions, 1 if form.get("active") else 0,
                 int(form.get("sort") or 100), rid),
            )
            msg = "Berichtsart gespeichert."
        else:
            key = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") + f"_{db.now()[-8:].replace(':', '')}"
            conn.execute(
                "INSERT INTO report_types (key, name, description, instructions, active, sort) VALUES (?, ?, ?, ?, 1, ?)",
                (key, name, form.get("description", "").strip(), instructions, int(form.get("sort") or 100)),
            )
            msg = "Berichtsart erstellt."
        db.audit(conn, admin, "berichtsart_geaendert", name)
    return redirect("/admin/report-types", msg, request)


@app.get("/admin/audit", response_class=HTMLResponse)
def admin_audit(request: Request):
    require_admin(request)
    with db.get_conn() as conn:
        entries = conn.execute("SELECT * FROM audit ORDER BY id DESC LIMIT 500").fetchall()
    return render(request, "admin_audit.html", {"entries": entries})
