"""NAS-Snapshots: nur vollständig erfolgreiche Scans ersetzen den letzten Stand.

Ob sich eine Datei seit dem letzten erfolgreichen Scan geändert hat, prüft der
Scan über Größe, Zeitstempel und eine Inhaltsprobe (erste 64 KB). Unveränderte
Dateien werden dadurch nicht erneut komplett eingelesen und verarbeitet.

`Media.sweep` entfernt aufbereitete Bilddateien, die keinem Gruppenstand und
keinem Dokument zugeordnet sind. So
wachsen Datenordner, Datenbank und Backups nicht endlos; Geräte melden sich
innerhalb weniger Sekunden neu an und laden die verbliebenen Inhalte.
"""

import hashlib
import io
import os
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps

from player.cache import ASSET_ID as ASSET_ID_RE
from server.assets import asset_lock, referenced_assets

IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
Image.MAX_IMAGE_PIXELS = 45_000_000
HEAD_BYTES = 65536  # First content block recorded per file for a cheap change check.


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def within(root, relative):
    root = root.resolve()
    part = Path(relative)
    if part.is_absolute() or ".." in part.parts or ":" in relative or "\\" in relative:
        raise ValueError("Nur relative NAS-Pfade ohne '..' sind erlaubt")
    result = (root / part).resolve()
    if not result.is_relative_to(root):
        raise ValueError("Pfad liegt außerhalb des freigegebenen Ordners")
    return result


class Media:
    def __init__(self, config, db):
        self.config, self.db = config, db
        self.assets = config.data_dir / "assets"
        self.assets.mkdir(parents=True, exist_ok=True)
        self.lock = asset_lock(config.data_dir)

    def assets_available(self, ids):
        descriptors = self.db.get_many("asset", ids)
        return bool(ids) and all(
            id in descriptors
            and (path := self.assets / (id + ".jpg")).is_file()
            and path.stat().st_size == descriptors[id].get("bytes")
            for id in ids
        )

    def upload_document(self, data, suffix, document):
        # Keep the lock until publication, including when ingest reuses an old file.
        with self.lock:
            assets = self.ingest(data, suffix)
            return self.db.put("document", {**document, "assets": assets})

    def image_asset(self, image):
        image = ImageOps.exif_transpose(image)
        image.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
        if image.mode in ("RGBA", "LA") or "transparency" in image.info:
            rgba = image.convert("RGBA")
            canvas = Image.new("RGB", rgba.size, "white")
            canvas.paste(rgba, mask=rgba.getchannel("A"))
        else:
            canvas = image.convert("RGB")
        stream = io.BytesIO()
        canvas.save(stream, "JPEG", quality=88, optimize=True)
        data = stream.getvalue()
        id = hashlib.sha256(data).hexdigest()
        path = self.assets / (id + ".jpg")
        if not path.is_file() or path.read_bytes() != data:
            temp = path.with_suffix(".tmp")
            temp.write_bytes(data)
            os.replace(temp, path)
        asset = {"id": id, "sha256": id, "bytes": len(data), "width": canvas.width, "height": canvas.height}
        self.db.put("asset", asset)
        return id

    def ingest(self, data, suffix):
        if len(data) > self.config.max_upload:
            raise ValueError("Datei ist größer als 40 MB")
        if suffix not in IMAGE_TYPES | {".pdf"}:
            raise ValueError("Bitte JPG, PNG, WebP, BMP oder PDF verwenden")
        source_id = hashlib.sha256(data + suffix.encode() + b"render-v1").hexdigest()
        with self.lock:
            cached = self.db.get("source", source_id)
            if cached and self.assets_available(cached["assets"]):
                return cached["assets"]
            if suffix == ".pdf":
                import pypdfium2 as pdfium

                result = []
                # PDFium is not thread-safe. All rendering shares this lock.
                with pdfium.PdfDocument(data) as pdf:
                    if len(pdf) < 1 or len(pdf) > 30:
                        raise ValueError("PDF muss 1 bis 30 Seiten enthalten")
                    for index in range(len(pdf)):
                        page = pdf[index]
                        try:
                            width, height = page.get_size()
                            if min(width, height) <= 0:
                                raise ValueError("Ungültiges PDF-Seitenformat")
                            bitmap = page.render(scale=min(1920 / width, 1920 / height))
                            try:
                                result.append(self.image_asset(bitmap.to_pil()))
                            finally:
                                bitmap.close()
                        finally:
                            page.close()
            else:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(io.BytesIO(data)) as img:
                        result = [self.image_asset(img)]
            self.db.put("source", {"id": source_id, "assets": result})
            return result

    def scan(self):
        with self.lock:
            for group in self.db.all("group"):
                self.scan_group(group)
            self.sweep()

    # Failed or abandoned processing leaves files briefly available for reuse.
    # Active processing is protected by the lock, not by this age limit.
    sweep_grace_seconds = 300

    def sweep(self):
        with self.lock:
            self._sweep()

    def _sweep(self):
        # Entfernt aufbereitete Bilder ohne aktive Zuordnung: Fotos aus gelöschten
        # NAS-Dateien, gelöschte Dokumente und alte Verarbeitungsreste. Datenordner,
        # Datenbank und Backups wachsen dadurch nicht endlos.
        keep = referenced_assets(self.db)
        now = time.time()
        for path in sorted(self.assets.iterdir()):
            if not (path.is_file() and path.suffix == ".jpg" and ASSET_ID_RE.fullmatch(path.stem)):
                continue
            if path.stem in keep or path.stat().st_mtime > now - self.sweep_grace_seconds:
                continue
            path.unlink(missing_ok=True)
            self.db.delete("asset", path.stem)
        # Ohne vorhandene Dateien ist der Eingabe-Cache wertlos; ingest() rendert dann neu.
        for source in self.db.all("source"):
            asset_ids = source.get("assets", [])
            if not asset_ids or any(
                not (self.assets / (asset_id + ".jpg")).exists() for asset_id in asset_ids
            ):
                self.db.delete("source", source["id"])

    @staticmethod
    def head_signature(path):
        with path.open("rb") as stream:
            return hashlib.sha256(stream.read(HEAD_BYTES)).hexdigest()

    @staticmethod
    def record_head(data):
        return hashlib.sha256(data[:HEAD_BYTES]).hexdigest()

    @staticmethod
    def rounded_mtime(stat):
        # Rounded to milliseconds: SMB shares may only report whole seconds, local disks more.
        return round(float(stat.st_mtime), 3), stat.st_size

    def scan_group(self, group):
        previous = self.db.get("snapshot", group["id"]) or {}
        # Unchanged-file reuse only applies if the previous scan covered the same sources
        # and recorded the current signature fields (snapshots from older versions do not).
        same_sources = (
            bool(previous)
            and previous.get("folder") == group["folder"]
            and previous.get("plan_path") == group.get("plan_path", "")
            and "photo_entries" in previous
            and "plan_sign" in previous
        )
        previous_photos = {entry["path"]: entry for entry in previous.get("photo_entries", [])}
        try:
            if not (self.config.nas_root / ".bilderrahmen-source").is_file():
                raise OSError("NAS-Marker fehlt")
            directory = within(self.config.nas_root, group["folder"])
            if not directory.is_dir():
                raise OSError("Gruppenordner fehlt")
            plan_path = within(directory, group["plan_path"]) if group.get("plan_path") else None
            found = []

            # os.walk raises on inaccessible directories rather than reporting an empty success.
            def fail(error):
                raise error

            for root, dirs, names in os.walk(directory, onerror=fail, followlinks=False):
                dirs[:] = [
                    d for d in dirs if not d.startswith((".", "@")) and not (Path(root) / d).is_symlink()
                ]
                for name in names:
                    path = Path(root) / name
                    if name.startswith((".", "@")) or path.is_symlink():
                        continue
                    if path.suffix.lower() not in IMAGE_TYPES or path.resolve() == plan_path:
                        continue
                    found.append((str(path.relative_to(directory)), path))
            if len(found) > 2000:
                raise ValueError("Höchstens 2000 Fotos pro Gruppe")
            # Exact paths keep entries unique even when only the letter case differs; the
            # casefold sort keeps the slideshow order stable like before.
            found.sort(key=lambda item: (item[0].casefold(), item[0]))
            photos, photo_entries = [], []
            for relative, path in found:
                stat = path.stat()
                if stat.st_size > self.config.max_upload:
                    raise ValueError("Ein Foto ist größer als 40 MB")
                mtime, size = self.rounded_mtime(stat)
                stored = previous_photos.get(relative) if same_sources else None
                # Identical size and timestamp to the last successful scan plus an identical
                # first content block: reuse the already verified assets without re-reading
                # the file content.
                unchanged = (
                    stored is not None
                    and stored["mtime"] == mtime
                    and stored["size"] == size
                    and self.head_signature(path) == stored["head"]
                    and self.assets_available(stored["assets"])
                )
                if unchanged:
                    assets, head = list(stored["assets"]), stored["head"]
                else:
                    data = path.read_bytes()
                    assets = self.ingest(data, path.suffix.lower())
                    mtime, size, head = (
                        *self.rounded_mtime(path.stat()),
                        self.record_head(data),
                    )
                photos.extend(assets)
                photo_entries.append(
                    {"path": relative, "mtime": mtime, "size": size, "head": head, "assets": assets}
                )
            plan, plan_sign = [], None
            if plan_path:
                stat = plan_path.stat()
                if stat.st_size > self.config.max_upload:
                    raise ValueError("Dienstplan ist größer als 40 MB")
                mtime, size = self.rounded_mtime(stat)
                previous_plan_sign = previous.get("plan_sign") if same_sources else None
                if (
                    previous_plan_sign is not None
                    and previous_plan_sign["mtime"] == mtime
                    and previous_plan_sign["size"] == size
                    and self.head_signature(plan_path) == previous_plan_sign["head"]
                    and self.assets_available(previous.get("plan", []))
                ):
                    plan, plan_sign = list(previous.get("plan", [])), previous_plan_sign
                else:
                    data = plan_path.read_bytes()
                    plan = self.ingest(data, plan_path.suffix.lower())
                    mtime, size = self.rounded_mtime(plan_path.stat())
                    plan_sign = {"mtime": mtime, "size": size, "head": self.record_head(data)}
            snapshot = {
                "id": group["id"],
                "photos": photos,
                "plan": plan,
                "photo_entries": photo_entries,
                "plan_sign": plan_sign,
                "folder": group["folder"],
                "plan_path": group.get("plan_path", ""),
                "plan_public": group.get("plan_public", False),
                "last_sync": utcnow(),
                "error": "",
            }
            self.db.put("snapshot", snapshot)
            if group.get("document_list_migrated") and group.get("plan_path"):
                # Continue updating an imported NAS document while it still exists.
                self.db.mutate(
                    "document",
                    "nas-" + group["id"],
                    {
                        "assets": plan,
                        "legacy_nas_folder": group["folder"],
                        "legacy_nas_path": group["plan_path"],
                    },
                )
        except Exception as error:
            # Deliberately no paths, document contents, or credentials in status/logs.
            detail = (
                str(error)
                if isinstance(error, ValueError)
                else "NAS nicht lesbar oder Datei beschädigt; letzter Stand bleibt erhalten."
            )
            fallback = self.db.get("snapshot", group["id"]) or {
                "id": group["id"],
                "photos": [],
                "plan": [],
            }
            fallback["error"] = detail[:160]
            self.db.put("snapshot", fallback)

    def descriptors(self, ids):
        return {id: self.db.get("asset", id) for id in set(ids) if self.db.get("asset", id)}
