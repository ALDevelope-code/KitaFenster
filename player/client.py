import json
import socket
import ssl
import threading
import time
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from player.cache import Cache, atomic_json


def local_ip_for_server(url):
    """Return the player's source address on the route toward its server."""
    parsed = urlsplit(url)
    if not parsed.hostname:
        return None
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return None
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            addresses = socket.getaddrinfo(parsed.hostname, port, family, socket.SOCK_DGRAM)
        except OSError:
            continue
        for _, kind, protocol, _, address in addresses:
            try:
                with socket.socket(family, kind, protocol) as connection:
                    connection.connect(address)
                    local = connection.getsockname()[0]
                    if local not in ("0.0.0.0", "::"):
                        return local
            except OSError:
                continue
    return None


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Weiterleitungen sind für Gerätezugriffe deaktiviert")


class API:
    def __init__(self, url, token="", ca_file=None):
        parsed = urlsplit(url)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Bitte eine HTTP(S)-Serveradresse ohne Zugangsdaten angeben")
        self.url, self.token = url.rstrip("/"), token
        self.opener = build_opener(
            NoRedirect(), HTTPSHandler(context=ssl.create_default_context(cafile=ca_file))
        )

    def request(self, path, body=None, limit=8 * 1024 * 1024):
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = Request(
            self.url + path, data=json.dumps(body).encode() if body is not None else None, headers=headers
        )
        with self.opener.open(req, timeout=20) as response:
            data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Antwort überschreitet Größenlimit")
        return data

    def sync(self, state):
        return json.loads(self.request("/api/device/sync", state))

    def motion(self, sample):
        return json.loads(self.request("/api/device/motion", {"sample": sample}))

    def asset(self, id, size):
        return self.request("/api/device/assets/" + id, limit=size)


class SyncWorker:
    def __init__(self, config, api=None):
        self.cache = Cache(config["cache_dir"], config.get("cache_limit_mb", 1024) * 1024 * 1024)
        self.api = api or API(config["server_url"], config["token"], config.get("ca_file"))
        self.server_url = config.get("server_url", getattr(self.api, "url", None))
        self.manifest = self.cache.load()
        self.verify_cache = True
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.restart = threading.Event()
        self.poll_seconds = max(5, config.get("poll_seconds", 15))
        self.state_path = self.cache.root / "state.json"
        try:
            persisted = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            persisted = {}
        self.acked = persisted.get("ack", [])[-100:]
        self.status = {
            "mode": "starting",
            "reason": "Startet",
            "revision": "",
            "last_sync": persisted.get("last_sync"),
            "error": "",
        }
        self.player_error = ""
        self.motion_sample = None
        self.motion_sample_at = 0
        self.diagnostics_active = False
        self.storage_reporting = False
        self.ip_reporting = False

    def snapshot(self):
        with self.lock:
            return self.manifest

    def report(self, mode, reason, error="", motion=None):
        with self.lock:
            self.status.update(mode=mode, reason=reason)
            self.player_error = error
            self.motion_sample = {**motion, "mode": mode, "reason": reason} if motion else None
            self.motion_sample_at = time.monotonic()

    def forget(self):
        with self.lock:
            self.manifest = None
        self.cache.clear()

    @staticmethod
    def access_revoked(old, new):
        old_policy, new_policy = old.get("policy", {}), new.get("policy", {})
        for key in ("group_id", "allow_internal", "plan_public", "folder", "plan_path", "plan_id"):
            if old_policy.get(key) != new_policy.get(key):
                return True
        if old_policy.get("plan_access") and not new_policy.get("plan_access"):
            return True
        for key in ("documents", "common_documents"):
            if set(old_policy.get(key, [])) - set(new_policy.get(key, [])):
                return True
        return False

    def sync_once(self):
        with self.lock:
            status = {**self.status, "ack": self.acked.copy()}
            status["error"] = "; ".join(filter(None, (self.player_error, status["error"])))[:160]
        if self.storage_reporting:
            status["storage"] = self.cache.storage()
        if self.ip_reporting and self.server_url:
            local_ip = local_ip_for_server(self.server_url)
            if local_ip:
                status["local_ip"] = local_ip
        response = self.api.sync(status)
        # Old servers do not advertise this endpoint. Keep the legacy heartbeat unchanged.
        self.diagnostics_active = response.get("motion_diagnostics", False)
        self.storage_reporting = response.get("storage_reporting", False)
        self.ip_reporting = response.get("ip_reporting", False)
        manifest = response["manifest"]
        old = self.snapshot()
        if old and self.access_revoked(old, manifest):
            # Revoked internal access / reassignment must not survive a failed download.
            self.forget()
            old = None
        self.cache.validate(manifest)
        missing = 0
        if (
            self.verify_cache
            or not old
            or old["revision"] != manifest["revision"]
            or self.snapshot() is None
            or self.cache.can_expand(old, manifest)
        ):
            stored, missing = self.cache.install(manifest, self.api.asset)
            self.verify_cache = False
            with self.lock:
                self.manifest = stored
        else:
            missing = sum(
                descriptor["bytes"]
                for id, descriptor in manifest["assets"].items()
                if id not in old["assets"]
            )
        now = datetime.now(timezone.utc).isoformat()
        with self.lock:
            self.status.update(
                last_sync=now, error=response.get("nas_error", ""), revision=manifest["revision"]
            )
            if missing:
                amount = (missing + 1024 * 1024 - 1) // (1024 * 1024)
                if self.cache.disk_missing_bytes:
                    note = f"Speicherreserve: {amount} MiB Inhalte ausgelassen. Platz auf dem Pi freigeben."
                else:
                    note = f"Cache reicht für {amount} MiB Inhalte nicht. Bitte cache_limit_mb erhöhen."
                self.status["error"] = "; ".join(filter(None, (self.status["error"], note)))[:160]
        restart = False
        for command in response.get("commands", []):
            if command["id"] not in self.acked:
                if command["kind"] == "restart":
                    restart = True
                self.acked.append(command["id"])
        self.acked = self.acked[-100:]
        # Persist before restart, so redelivery cannot cause a restart loop.
        atomic_json(self.state_path, {"ack": self.acked, "last_sync": now})
        if restart:
            self.restart.set()

    def diagnostics_once(self):
        with self.lock:
            sample = (
                {**self.motion_sample, "sample_age_seconds": max(0, time.monotonic() - self.motion_sample_at)}
                if self.motion_sample
                else None
            )
        self.diagnostics_active = self.api.motion(sample).get("active", False)

    def run(self):
        delay = self.poll_seconds
        next_sync, next_diagnostic = 0, 0
        while not self.stop.is_set():
            if time.monotonic() >= next_sync:
                try:
                    self.sync_once()
                    delay = self.poll_seconds
                except HTTPError as error:
                    if error.code in (401, 403):
                        self.forget()
                        self.diagnostics_active = False
                        message = "Gerätezugriff widerrufen. Bitte neu koppeln."
                    else:
                        message = "Server momentan nicht erreichbar; lokaler Stand bleibt aktiv."
                    with self.lock:
                        self.status["error"] = message
                    delay = min(60, delay * 2)
                except Exception:
                    with self.lock:
                        self.status["error"] = "Synchronisierung fehlgeschlagen; lokaler Stand bleibt aktiv."
                    delay = min(60, delay * 2)
                next_sync = time.monotonic() + delay
            if self.restart.is_set() or self.stop.is_set():
                break
            if self.diagnostics_active and time.monotonic() >= next_diagnostic:
                try:
                    self.diagnostics_once()
                    next_diagnostic = time.monotonic() + 1
                except Exception:
                    # Diagnostics must never disrupt playback, cache or regular sync.
                    next_diagnostic = time.monotonic() + 5
            wake_at = min(next_sync, next_diagnostic) if self.diagnostics_active else next_sync
            self.stop.wait(max(0, wake_at - time.monotonic()))

    def start(self):
        thread = threading.Thread(target=self.run, name="nas-sync", daemon=True)
        thread.start()
        return thread
