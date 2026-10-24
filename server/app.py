import asyncio
import base64
import contextlib
import json
import secrets
import threading
import time
from contextlib import asynccontextmanager
from ipaddress import ip_address
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from server.branding import DEFAULT_BRANDING, MAX_LOGO_BYTES, normalize_logo, public_branding
from server.config import Config
from server.db import Database, uid
from server.documents import (
    delete_document,
    document_usage,
    list_assignment,
    migrate_document_lists,
    save_document_metadata,
    save_list_assignment,
    unlink_group,
    update_all_group_assignments,
)
from server.manifest import device_status, document_allowed, manifest_for
from server.media import IMAGE_TYPES, Media, utcnow, within
from server.models import (
    BrandingInput,
    Control,
    DeviceInput,
    DocumentInput,
    DocumentListInput,
    GroupInput,
    Heartbeat,
    Login,
    MotionReport,
    NoticeInput,
    OperatingHours,
    Pair,
    PlanAssignment,
)
from server.motion_diagnostics import MotionDiagnostics
from server.security import Limiter, digest, password_matches, secure_equals, set_admin
from shared.schedule import document_references, matches, resolve, slides
from shared.source import source_archive


def create_app(config=None):
    config = config or Config.from_env()
    db = Database(config.data_dir / "kita.sqlite3")
    if config.admin_password is not None:
        set_admin(db, config.admin_username, config.admin_password, only_if_changed=True)
    media = Media(config, db)
    limiter = Limiter()
    source_lock = threading.Lock()
    source_cache = {"archive": None}
    if not db.get("branding", "site"):
        db.put("branding", DEFAULT_BRANDING)
    if not db.all("group"):
        for name in ("Gruppe 1", "Gruppe 2", "Gruppe 3"):
            db.put("group", {"id": uid(), "name": name, "folder": name, "plan_path": "", "plan_id": None})

    migrate_document_lists(db)

    @asynccontextmanager
    async def lifespan(app):
        async def scan_loop():
            while True:
                await asyncio.to_thread(media.scan)
                await asyncio.sleep(config.scan_seconds)

        task = asyncio.create_task(scan_loop()) if config.background_scan else None
        yield
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title="KitaFenster", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.db, app.state.media, app.state.config = db, media, config
    diagnostics = MotionDiagnostics()
    app.state.motion_diagnostics = diagnostics

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, error: RequestValidationError):
        # Raw invalid values can contain lone surrogates that JSON cannot encode.
        def safe(value):
            return str(value).encode("utf-8", "backslashreplace").decode("utf-8")

        return JSONResponse(
            {
                "detail": [
                    {
                        "loc": [safe(part) if isinstance(part, str) else part for part in item["loc"]],
                        "msg": safe(item["msg"]),
                        "type": safe(item["type"]),
                    }
                    for item in error.errors()
                ]
            },
            status_code=422,
        )

    @app.middleware("http")
    async def headers(request, call_next):
        # Multipart parser is also bounded before it starts buffering uploads.
        size = request.headers.get("content-length", "0")
        logo_upload = request.url.path == "/api/admin/branding/logo" and request.method == "POST"
        group_edit = (
            request.url.path.startswith("/api/admin/groups/")
            and request.url.path.endswith("/edit")
            and request.method == "POST"
        )
        image_upload = logo_upload or group_edit
        size_limit = MAX_LOGO_BYTES + 65536 if image_upload else config.max_upload + 1024 * 1024
        if not size.isdigit() or int(size) > size_limit:
            return JSONResponse({"detail": "Anfrage zu groß"}, status_code=413)
        if (request.url.path.startswith("/api/admin/upload") or image_upload) and not request.headers.get(
            "content-length"
        ):
            return JSONResponse({"detail": "Content-Length erforderlich"}, status_code=411)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        elif request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    def admin(request: Request):
        token = request.cookies.get("kita_session", "")
        with db.connect() as connection:
            session = connection.execute(
                "SELECT * FROM sessions WHERE token=? AND expires>?", (digest(token), time.time())
            ).fetchone()
        if not session:
            raise HTTPException(401, "Bitte anmelden")
        if request.method not in ("GET", "HEAD"):
            if not secure_equals(request.headers.get("x-csrf-token", ""), session["csrf"]):
                raise HTTPException(403, "Sitzung ungültig; bitte neu anmelden")
        return session

    def device_auth(request: Request):
        token = request.headers.get("authorization", "")
        if not token.startswith("Bearer "):
            raise HTTPException(401, "Geräteanmeldung erforderlich")
        with db.connect() as connection:
            row = connection.execute(
                "SELECT device_id FROM device_tokens WHERE token=?", (digest(token[7:]),)
            ).fetchone()
        device = db.get("device", row[0]) if row else None
        if not device:
            raise HTTPException(401, "Gerätezugriff widerrufen")
        return device

    def required(kind, id):
        value = db.get(kind, id)
        if not value:
            raise HTTPException(404, "Eintrag nicht gefunden")
        return value

    def target_exists(target):
        if target.kind != "all":
            required(target.kind, target.id)

    def pairing(device_id):
        code = secrets.token_hex(8).upper()
        with db.connect() as connection:
            connection.execute("DELETE FROM pairing WHERE device_id=? OR expires<?", (device_id, time.time()))
            connection.execute(
                "INSERT INTO pairing VALUES (?,?,?)", (digest(code), device_id, time.time() + 900)
            )
        return {"code": code, "expires_in": 900}

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.2.3"}

    @app.get("/api/license")
    def license_text():
        root = Path(__file__).resolve().parents[1]
        return Response(
            (root / "NOTICE").read_text(encoding="utf-8")
            + "\n"
            + (root / "LICENSE").read_text(encoding="utf-8"),
            media_type="text/plain",
        )

    @app.get("/api/source")
    def download_source():
        with source_lock:
            if source_cache["archive"] is None:
                source_cache["archive"] = source_archive(Path(__file__).resolve().parents[1])
        return Response(
            source_cache["archive"],
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="kitafenster-source.zip"'},
        )

    @app.get("/api/branding")
    def branding():
        # Only these presentation fields are public, including on the login page.
        return public_branding(db)

    @app.get("/api/branding/logo")
    def branding_logo():
        value = db.get("branding", "site")
        if value and value["logo"]:
            return Response(base64.b64decode(value["logo"]), media_type="image/png")
        return FileResponse(Path(__file__).parent / "static" / "default-logo.svg", media_type="image/svg+xml")

    @app.put("/api/admin/branding", dependencies=[Depends(admin)])
    def save_branding(body: BrandingInput):
        db.mutate("branding", "site", body.model_dump())
        return public_branding(db)

    @app.post("/api/admin/branding/logo", dependencies=[Depends(admin)])
    async def upload_logo(file: UploadFile = File(...)):
        try:
            content = await file.read(MAX_LOGO_BYTES + 1)
        finally:
            await file.close()
        if len(content) > MAX_LOGO_BYTES:
            raise HTTPException(413, "Das Logo darf höchstens 2 MB groß sein.")
        try:
            changes = await asyncio.to_thread(normalize_logo, content)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        db.mutate("branding", "site", changes)
        return public_branding(db)

    @app.delete("/api/admin/branding/logo", dependencies=[Depends(admin)])
    def reset_logo():
        db.mutate("branding", "site", {"logo": None, "logo_hash": "default"})
        return public_branding(db)

    @app.post("/api/login")
    def login(body: Login, request: Request, response: Response):
        address = request.client.host if request.client else "local"
        limit_key = "login:" + address
        if limiter.blocked(limit_key):
            raise HTTPException(429, "Zu viele Versuche. Bitte in fünf Minuten erneut versuchen.")
        with db.connect() as connection:
            row = connection.execute("SELECT data FROM auth WHERE key='admin'").fetchone()
        if not row:
            raise HTTPException(
                503,
                "Zuerst ADMIN_PASSWORD in .env setzen und den Container neu erstellen oder 'python -m server.manage admin' ausführen.",
            )
        account = json.loads(row[0])
        valid_password = password_matches(body.password, account["password"])
        if not secure_equals(body.username, account["username"]) or not valid_password:
            limiter.record_failure(limit_key)
            raise HTTPException(401, "Benutzername oder Passwort stimmt nicht")
        limiter.reset(limit_key)
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with db.connect() as connection:
            connection.execute("DELETE FROM sessions WHERE expires<?", (time.time(),))
            connection.execute(
                "INSERT INTO sessions VALUES (?,?,?)", (digest(token), csrf, time.time() + 12 * 3600)
            )
        response.set_cookie(
            "kita_session",
            token,
            max_age=12 * 3600,
            httponly=True,
            secure=config.secure_cookie,
            samesite="strict",
        )
        return {"csrf": csrf}

    @app.get("/api/session")
    def session(auth=Depends(admin)):
        return {"csrf": auth["csrf"]}

    @app.post("/api/logout")
    def logout(response: Response, auth=Depends(admin)):
        with db.connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token=?", (auth["token"],))
        response.delete_cookie("kita_session")
        return {"ok": True}

    @app.get("/api/admin/state", dependencies=[Depends(admin)])
    def state():
        groups = db.all("group")
        return {
            "groups": [group_view(g) for g in groups],
            "devices": [device_status(db, d) for d in db.all("device")],
            "notices": db.all("notice"),
            "operating_hours": db.get("operating_hours", "global") or OperatingHours().model_dump(),
            "documents": [{**d, "list_assignment": list_assignment(d, groups)} for d in db.all("document")],
            "snapshots": [
                {key: value for key, value in snapshot.items() if key != "photo_entries"}
                for snapshot in db.all("snapshot")
            ],
            "server_time": utcnow(),
            "server_version": health()["version"],
            "branding": public_branding(db),
        }

    def group_view(group):
        return {
            **group,
            "icon_url": f"/api/admin/groups/{group['id']}/icon?v={group['icon_hash']}"
            if group.get("icon_hash")
            else None,
        }

    def store_group(id, body, icon=None):
        try:
            folder = within(config.nas_root, body.folder)
            if body.plan_path:
                within(folder, body.plan_path)
        except ValueError as error:
            raise HTTPException(422, str(error))
        with db.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if id == "new":
                group = {"id": uid(), "plan_id": None}
            else:
                row = connection.execute(
                    "SELECT data FROM entities WHERE kind='group' AND id=?", (id,)
                ).fetchone()
                if row is None:
                    raise HTTPException(404, "Gruppe nicht gefunden")
                group = json.loads(row[0])
            group.update(body.model_dump(exclude_unset=True))
            if icon is not None:
                group["icon_hash"] = icon.get("logo_hash")
                if icon:
                    Database.write(connection, "group_icon", {"id": group["id"], **icon})
                else:
                    connection.execute("DELETE FROM entities WHERE kind='group_icon' AND id=?", (id,))
            Database.write(connection, "group", group)
        return group_view(group)

    @app.put("/api/admin/groups/{id}", dependencies=[Depends(admin)])
    def save_group(id: str, body: GroupInput):
        required("group", id)
        return store_group(id, body)

    @app.post("/api/admin/groups", dependencies=[Depends(admin)])
    def add_group(body: GroupInput):
        return store_group("new", body)

    @app.get("/api/admin/groups/{id}/icon", dependencies=[Depends(admin)])
    def group_icon(id: str):
        required("group", id)
        icon = required("group_icon", id)
        return Response(base64.b64decode(icon["logo"]), media_type="image/png")

    @app.post("/api/admin/groups/{id}/edit", dependencies=[Depends(admin)])
    async def edit_group(
        id: str,
        data: str = Form(..., max_length=4096),
        icon_action: Literal["keep", "replace", "remove"] = Form("keep"),
        file: UploadFile | None = File(None),
    ):
        try:
            if id != "new":
                required("group", id)
            try:
                body = GroupInput.model_validate_json(data)
            except ValidationError as error:
                raise HTTPException(422, "Bitte Gruppenname und gültige NAS-Pfade angeben.") from error
            icon = None
            if icon_action == "replace":
                if file is None:
                    raise HTTPException(422, "Bitte ein Gruppenbild auswählen.")
                content = await file.read(MAX_LOGO_BYTES + 1)
                if len(content) > MAX_LOGO_BYTES:
                    raise HTTPException(413, "Das Gruppenbild darf höchstens 2 MB groß sein.")
                try:
                    icon = await asyncio.to_thread(normalize_logo, content, label="Gruppenbild", size=256)
                except ValueError as error:
                    raise HTTPException(422, str(error)) from error
            elif file is not None:
                raise HTTPException(422, "Zum Hochladen bitte das Gruppenbild ersetzen.")
            elif icon_action == "remove":
                icon = {}
            return store_group(id, body, icon)
        finally:
            if file is not None:
                await file.close()

    def validate_documents(ids, device=None):
        for id in ids:
            document = required("document", id)
            if document["kind"] != "plan":
                raise HTTPException(422, "Bitte ein Dokument auswählen; Meldungsbilder gehören zu Meldungen.")
            if device and not document_allowed(document, device, required("group", device["group_id"])):
                raise HTTPException(
                    422,
                    "Das Dokument „" + document["name"] + "“ ist nur intern. "
                    "Unter Inhalte für Eltern freigeben oder einen internen Bilderrahmen verwenden.",
                )

    @app.post("/api/admin/devices", dependencies=[Depends(admin)])
    def add_device(body: DeviceInput):
        required("group", body.group_id)
        validate_documents(document_references(body.settings.model_dump()), body.model_dump())
        device = db.put(
            "device", {"id": uid(), **body.model_dump(), "manual": None, "last_seen": None, "reported": {}}
        )
        return {"device": device, **pairing(device["id"])}

    @app.put("/api/admin/devices/{id}", dependencies=[Depends(admin)])
    def save_device(id: str, body: DeviceInput):
        required("device", id)
        required("group", body.group_id)
        validate_documents(document_references(body.settings.model_dump()), body.model_dump())
        return db.mutate("device", id, body.model_dump())

    @app.get("/api/admin/devices/{id}/motion", dependencies=[Depends(admin)])
    def motion_status(id: str):
        device = required("device", id)
        return {
            **diagnostics.snapshot(id),
            "settings": device["settings"].get("motion", {}),
            "last_seen": device.get("last_seen"),
            "reported": device.get("reported", {}),
        }

    @app.post("/api/admin/devices/{id}/motion", dependencies=[Depends(admin)])
    def start_motion_status(id: str):
        required("device", id)
        diagnostics.start(id)
        return motion_status(id)

    @app.post("/api/admin/devices/{id}/pair", dependencies=[Depends(admin)])
    def repair_device(id: str):
        required("device", id)
        return pairing(id)

    @app.delete("/api/admin/devices/{id}", dependencies=[Depends(admin)])
    def remove_device(id: str):
        required("device", id)
        diagnostics.discard(id)
        with db.connect() as connection:
            connection.execute("DELETE FROM device_tokens WHERE device_id=?", (id,))
            connection.execute("DELETE FROM pairing WHERE device_id=?", (id,))
            connection.execute("DELETE FROM commands WHERE device_id=?", (id,))
            connection.execute("DELETE FROM entities WHERE kind='device' AND id=?", (id,))
        return {"ok": True}

    @app.post("/api/admin/control", dependencies=[Depends(admin)])
    def control(body: Control):
        target_exists(body.target)
        changed = []
        with db.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for row in connection.execute("SELECT data FROM entities WHERE kind='device'").fetchall():
                device = json.loads(row[0])
                if matches(body.target.model_dump(), device):
                    if body.area == "secondary" and not device["settings"].get("split", {}).get("enabled"):
                        continue
                    key = "manual" if body.area == "main" else "manual_secondary"
                    device[key] = {"mode": body.mode, "until": body.until} if body.mode else None
                    Database.write(connection, "device", device)
                    changed.append(device["id"])
        return {"changed": changed}

    @app.post("/api/admin/devices/{id}/commands/{kind}", dependencies=[Depends(admin)])
    async def command(id: str, kind: str):
        required("device", id)
        if kind not in ("sync", "restart"):
            raise HTTPException(422, "Unbekannter Befehl")
        if kind == "sync":
            await asyncio.to_thread(media.scan)
        command_id = uid()
        with db.connect() as connection:
            connection.execute("DELETE FROM commands WHERE created<? OR acked=1", (time.time() - 86400,))
            connection.execute(
                "INSERT INTO commands(id,device_id,kind,created) VALUES (?,?,?,?)",
                (command_id, id, kind, time.time()),
            )
        return {"id": command_id}

    @app.post("/api/admin/scan", dependencies=[Depends(admin)])
    async def scan():
        await asyncio.to_thread(media.scan)
        return {"snapshots": db.all("snapshot")}

    @app.put("/api/admin/notices/{id}", dependencies=[Depends(admin)])
    def save_notice(id: str, body: NoticeInput):
        target_exists(body.target)
        if body.image_id:
            document = required("document", body.image_id)
            if document["kind"] != "image":
                raise HTTPException(422, "Für Meldungen bitte ein Bild auswählen")
        if id != "new":
            required("notice", id)
        return db.put("notice", {"id": uid() if id == "new" else id, **body.model_dump()})

    @app.put("/api/admin/operating-hours", dependencies=[Depends(admin)])
    def save_operating_hours(body: OperatingHours):
        return db.put("operating_hours", {"id": "global", **body.model_dump()})

    @app.put("/api/admin/documents/{id}", dependencies=[Depends(admin)])
    def save_document(id: str, body: DocumentInput):
        return save_document_metadata(db, id, body.model_dump())

    @app.put("/api/admin/documents/{id}/list", dependencies=[Depends(admin)])
    def save_document_list(id: str, body: DocumentListInput):
        return save_list_assignment(db, id, body.model_dump())

    @app.get("/api/admin/documents/{id}/usage", dependencies=[Depends(admin)])
    def get_document_usage(id: str):
        return document_usage(db, id)

    @app.put("/api/admin/documents/{id}/groups", dependencies=[Depends(admin)])
    def assign_document_to_all_groups(id: str, body: PlanAssignment):
        return update_all_group_assignments(db, id, assign=True, plan_public=body.plan_public)

    @app.delete("/api/admin/documents/{id}/groups", dependencies=[Depends(admin)])
    def remove_all_group_assignments(id: str):
        return update_all_group_assignments(db, id, assign=False)

    @app.delete("/api/admin/documents/{id}/groups/{group_id}", dependencies=[Depends(admin)])
    def remove_group_assignment(id: str, group_id: str):
        return unlink_group(db, id, group_id)

    @app.delete("/api/admin/{kind}/{id}", dependencies=[Depends(admin)])
    def delete_content(kind: str, id: str, unlink: bool = False, revision: str | None = None):
        table = {"notices": "notice", "documents": "document"}.get(kind)
        if not table:
            raise HTTPException(404)
        if table == "document":
            with media.lock:
                result = delete_document(db, id, unlink=unlink, revision=revision)
                media.sweep()
                return result
        db.delete(table, id)
        return {"ok": True}

    @app.post("/api/admin/upload/{kind}", dependencies=[Depends(admin)])
    async def upload(
        kind: str,
        file: UploadFile = File(...),
        category: str = Form(default="", max_length=60),
        public: bool = Form(default=False),
    ):
        if kind not in ("image", "plan"):
            raise HTTPException(422, "Ungültiger Dateityp")
        category = category.strip() or ("Dokument" if kind == "plan" else "Meldungsbild")
        if any(ord(char) < 32 for char in category):
            raise HTTPException(422, "Bitte eine gültige Dokumentart angeben")
        suffix = Path(file.filename or "").suffix.lower()
        if kind == "image" and suffix not in IMAGE_TYPES:
            raise HTTPException(422, "Bitte eine Bilddatei auswählen")
        data = await file.read(config.max_upload + 1)
        await file.close()
        try:
            return await asyncio.to_thread(
                media.upload_document,
                data,
                suffix,
                {
                    "id": uid(),
                    "name": (file.filename or "Datei")[:120],
                    "kind": kind,
                    "category": category,
                    "public": public,
                    "created_at": utcnow(),
                },
            )
        except Exception:
            raise HTTPException(
                422, "Datei nicht lesbar. Erlaubt: JPG, PNG, WebP, BMP und PDF (max. 40 MB, 30 Seiten)."
            )

    @app.put("/api/admin/groups/{id}/plan/{document_id}", dependencies=[Depends(admin)])
    def assign_plan(id: str, document_id: str, body: PlanAssignment | None = None):
        group = required("group", id)
        if document_id == "none":
            return unlink_group(db, group["plan_id"], id) if group.get("plan_id") else group
        if document_id != "none":
            if required("document", document_id)["kind"] != "plan":
                raise HTTPException(422, "Bitte ein Dokument auswählen")
        return db.mutate(
            "group",
            id,
            {
                "plan_id": None if document_id == "none" else document_id,
                "plan_public": bool(body and body.plan_public),
            },
        )

    @app.get("/api/admin/preview/{id}", dependencies=[Depends(admin)])
    def preview(id: str, at: str | None = None):
        from shared.schedule import parse_time

        try:
            moment = parse_time(at)
            if moment and moment.tzinfo is None:
                raise ValueError()
        except ValueError:
            raise HTTPException(422, "Zeitpunkt benötigt eine Zeitzone")
        manifest = manifest_for(db, required("device", id))
        decision = resolve(manifest, moment)
        return {
            "manifest": manifest,
            "decision": decision,
            "slides": slides(manifest, decision),
            "secondary_slides": slides(manifest, decision["secondary"]) if decision.get("secondary") else [],
        }

    @app.get("/api/admin/assets/{id}", dependencies=[Depends(admin)])
    def admin_asset(id: str):
        required("asset", id)
        return FileResponse(media.assets / (id + ".jpg"), media_type="image/jpeg")

    @app.post("/api/device/pair")
    def pair(body: Pair, request: Request):
        address = request.client.host if request.client else "local"
        limit_key = "pair:" + address
        if limiter.blocked(limit_key, count=20):
            raise HTTPException(429, "Zu viele Kopplungsversuche")
        token = secrets.token_urlsafe(40)
        with db.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            code_hash = digest(body.code.replace(" ", "").upper())
            row = connection.execute(
                "SELECT * FROM pairing WHERE code=? AND expires>?", (code_hash, time.time())
            ).fetchone()
            if row:
                connection.execute("DELETE FROM pairing WHERE code=?", (code_hash,))
                connection.execute("DELETE FROM device_tokens WHERE device_id=?", (row["device_id"],))
                connection.execute(
                    "INSERT INTO device_tokens VALUES (?,?)", (digest(token), row["device_id"])
                )
        if not row:
            limiter.record_failure(limit_key)
            raise HTTPException(401, "Kopplungscode ungültig oder abgelaufen")
        limiter.reset(limit_key)
        return {"token": token, "device_id": row["device_id"]}

    @app.post("/api/device/sync")
    def sync(body: Heartbeat, request: Request, device=Depends(device_auth)):
        changes = {"last_seen": utcnow(), "reported": body.model_dump(exclude={"ack"})}
        if request.client:
            try:
                changes["last_ip"] = str(ip_address(request.client.host))
            except ValueError:
                pass
        updated = db.mutate("device", device["id"], changes)
        with db.connect() as connection:
            for ack in body.ack:
                connection.execute(
                    "UPDATE commands SET acked=1 WHERE id=? AND device_id=?", (ack, device["id"])
                )
            commands = [
                dict(r)
                for r in connection.execute(
                    "SELECT id,kind FROM commands WHERE device_id=? AND acked=0 AND created>? ORDER BY created",
                    (device["id"], time.time() - 86400),
                )
            ]
        manifest = manifest_for(db, updated)
        snapshot = db.get("snapshot", updated["group_id"]) or {}
        return {
            "manifest": manifest,
            "commands": commands,
            "server_time": utcnow(),
            "nas_sync": snapshot.get("last_sync"),
            "nas_error": snapshot.get("error", ""),
            "motion_diagnostics": diagnostics.snapshot(device["id"])["active"],
            "storage_reporting": True,
        }

    @app.post("/api/device/motion")
    def report_motion(body: MotionReport, device=Depends(device_auth)):
        sample = body.sample.model_dump() if body.sample is not None else None
        return {"active": diagnostics.report(device["id"], sample)}

    @app.get("/api/device/assets/{id}")
    def device_asset(id: str, device=Depends(device_auth)):
        if id not in manifest_for(db, device, descriptors=False)["assets"]:
            raise HTTPException(404, "Inhalt diesem Gerät nicht zugewiesen")
        return FileResponse(media.assets / (id + ".jpg"), media_type="image/jpeg")

    static = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static, check_dir=False), name="static")

    @app.get("/")
    def index():
        return FileResponse(static / "index.html")

    return app
