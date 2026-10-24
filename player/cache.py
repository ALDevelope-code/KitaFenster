import hashlib
import json
import os
import re
import shutil
from pathlib import Path

ASSET_ID = re.compile(r"^[a-f0-9]{64}$")
DOWNLOAD_HEADROOM = 32 * 1024 * 1024


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temp, 0o600)
    os.replace(temp, path)


class Cache:
    def __init__(self, root, max_bytes=1024 * 1024 * 1024):
        self.root = Path(root)
        self.assets = self.root / "assets"
        self.assets.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes
        self.manifest_path = self.root / "manifest.json"
        self.disk_missing_bytes = 0

    def storage(self):
        usage = shutil.disk_usage(self.root)
        return {
            "total_bytes": usage.total,
            "free_bytes": usage.free,
            "reserved_bytes": (usage.total + 9) // 10,
            "cache_limit_bytes": self.max_bytes,
        }

    def can_expand(self, stored, offered):
        used = sum(descriptor["bytes"] for descriptor in stored["assets"].values())
        room = self.max_bytes - used
        if room <= 0:
            return False
        storage = self.storage()
        writable = storage["free_bytes"] - storage["reserved_bytes"] - DOWNLOAD_HEADROOM
        if writable <= 0:
            return False
        return any(
            descriptor["bytes"] <= min(room, writable)
            for id, descriptor in offered["assets"].items()
            if id not in stored["assets"]
        )

    def load(self):
        try:
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            self.validate(manifest)
            return manifest
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def validate(self, manifest):
        if manifest["version"] != 1 or not isinstance(manifest["settings"], dict):
            raise ValueError("Unbekannte Konfiguration")
        # A stale or incomplete cache must not crash the render loop before it
        # can fetch a fresh manifest. Reject it instead of inventing opening hours.
        operating = manifest.get("operating_hours")
        if (
            not isinstance(operating, dict)
            or not isinstance(operating.get("enabled"), bool)
            or not isinstance(operating.get("timezone"), str)
            or not isinstance(operating.get("windows"), list)
        ):
            raise ValueError("Betriebszeiten fehlen oder sind ungültig. Konfiguration erneut abgleichen.")
        total = 0
        for id, descriptor in manifest["assets"].items():
            if not ASSET_ID.fullmatch(id) or descriptor["sha256"] != id:
                raise ValueError("Ungültige Datei-ID")
            size = descriptor["bytes"]
            if not isinstance(size, int) or not 0 < size <= 12 * 1024 * 1024:
                raise ValueError("Ungültige Dateigröße")
            total += size
        return total

    def path(self, id):
        if not ASSET_ID.fullmatch(id):
            raise ValueError("Ungültige Datei-ID")
        return self.assets / (id + ".jpg")

    @staticmethod
    def prune(manifest, installed):
        result = dict(manifest)
        if "photos" in result:
            result["photos"] = [id for id in result["photos"] if id in installed]
        if "plan" in result:
            result["plan"] = [id for id in result["plan"] if id in installed]
        if "documents" in result:
            result["documents"] = {
                key: {**document, "assets": assets}
                for key, document in result["documents"].items()
                if (assets := [id for id in document.get("assets", []) if id in installed])
            }
        if "notices" in result:
            result["notices"] = [
                {**notice, "image": None}
                if notice.get("image") and notice["image"] not in installed
                else notice
                for notice in result["notices"]
            ]
        result["assets"] = {
            id: descriptor for id, descriptor in manifest["assets"].items() if id in installed
        }
        return result

    def install(self, manifest, fetch):
        self.validate(manifest)
        self.disk_missing_bytes = 0
        storage = self.storage()
        minimum_free = storage["reserved_bytes"] + DOWNLOAD_HEADROOM
        disk_budget = max(0, storage["free_bytes"] - minimum_free)
        descriptors = manifest["assets"]
        priority = dict.fromkeys([*manifest.get("photos", []), *manifest.get("plan", []), *descriptors])
        installed = {}
        used = 0
        missing = 0
        for id in priority:
            if id not in descriptors:
                continue
            descriptor = descriptors[id]
            if used + descriptor["bytes"] > self.max_bytes:
                missing += descriptor["bytes"]
                continue
            path = self.path(id)
            if path.exists() and path.stat().st_size == descriptor["bytes"]:
                if hashlib.sha256(path.read_bytes()).hexdigest() == id:
                    used += descriptor["bytes"]
                    installed[id] = descriptor
                    continue
            if (
                descriptor["bytes"] > disk_budget
                or shutil.disk_usage(self.root).free - descriptor["bytes"] < minimum_free
            ):
                missing += descriptor["bytes"]
                self.disk_missing_bytes += descriptor["bytes"]
                continue
            data = fetch(id, descriptor["bytes"])
            if len(data) != descriptor["bytes"] or hashlib.sha256(data).hexdigest() != id:
                raise ValueError("Dateiprüfung fehlgeschlagen")
            temp = path.with_suffix(".tmp")
            with temp.open("wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, path)
            disk_budget -= descriptor["bytes"]
            used += descriptor["bytes"]
            installed[id] = descriptor
        if descriptors and not installed:
            if self.disk_missing_bytes:
                raise ValueError("Zu wenig freier Speicher für die Synchronisierung")
            raise ValueError("Cache-Limit zu klein für einen Inhalt; bitte cache_limit_mb erhöhen")
        stored = self.prune(manifest, installed)
        atomic_json(self.manifest_path, stored)
        self.collect(stored["assets"])
        return stored, missing

    def collect(self, allowed):
        for path in self.assets.iterdir():
            if path.is_file() and (
                path.suffix == ".tmp" or (path.suffix == ".jpg" and path.stem not in allowed)
            ):
                path.unlink(missing_ok=True)

    def clear(self):
        self.manifest_path.unlink(missing_ok=True)
        self.collect({})
