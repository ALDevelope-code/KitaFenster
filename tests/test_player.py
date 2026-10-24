import hashlib
import json

import pytest
from conftest import image_bytes, pair_device

from player.cache import Cache, atomic_json
from player.client import SyncWorker
from server.models import OperatingHours, Settings


def manifest(data, revision="1"):
    id = hashlib.sha256(data).hexdigest()
    return {
        "version": 1,
        "revision": revision,
        "settings": Settings().model_dump(),
        "group_id": "g",
        "device_id": "d",
        "group_name": "Gruppe 1",
        "policy": {"group_id": "g", "allow_internal": False},
        "photos": [id],
        "plan": [],
        "notices": [],
        "operating_hours": OperatingHours().model_dump(),
        "assets": {id: {"id": id, "sha256": id, "bytes": len(data)}},
    }


def test_incomplete_cached_configuration_does_not_block_start_and_resync(tmp_path):
    data = image_bytes()
    current = manifest(data)
    cache = Cache(tmp_path)
    cache.install(current, lambda *_: data)
    incomplete = {key: value for key, value in current.items() if key != "operating_hours"}
    atomic_json(cache.manifest_path, incomplete)

    class FreshAPI:
        def sync(self, _):
            return {"manifest": current}

        def asset(self, *_):
            pytest.fail("Intakte Bilder sollen beim erneuten Abgleich erhalten bleiben.")

    worker = SyncWorker({"cache_dir": str(tmp_path)}, api=FreshAPI())
    assert worker.snapshot() is None
    worker.sync_once()
    assert worker.snapshot() == current
    assert Cache(tmp_path).load() == current
    with pytest.raises(ValueError, match="Betriebszeiten"):
        cache.install(incomplete, lambda *_: data)
    assert Cache(tmp_path).load() == current


def test_atomic_cache_download_failure_deletion_and_restart(tmp_path):
    cache = Cache(tmp_path)
    first = image_bytes()
    m1 = manifest(first)
    cache.install(m1, lambda id, size: first)
    second = image_bytes("blue")
    m2 = manifest(second, "2")
    with pytest.raises(ValueError):
        cache.install(m2, lambda id, size: b"broken")
    assert Cache(tmp_path).load()["revision"] == "1"
    assert cache.path(m1["photos"][0]).exists()
    cache.install(m2, lambda id, size: second)
    assert not cache.path(m1["photos"][0]).exists()
    assert Cache(tmp_path).load()["revision"] == "2"
    m2["assets"] = {}
    m2["photos"] = []
    m2["revision"] = "3"
    cache.install(m2, lambda *args: None)
    assert list(cache.assets.iterdir()) == []


def test_cache_bounds_and_traversal(tmp_path):
    cache = Cache(tmp_path, max_bytes=10)
    with pytest.raises(ValueError):
        cache.install(manifest(image_bytes()), lambda *a: b"")
    with pytest.raises(ValueError):
        cache.path("../outside")


class LocalAPI:
    def __init__(self, client, headers):
        self.client, self.headers = client, headers
        self.offline = False
        self.fail_download = False

    def sync(self, body):
        if self.offline:
            raise OSError("offline")
        response = self.client.post("/api/device/sync", json=body, headers=self.headers)
        assert response.status_code == 200, response.text
        return response.json()

    def asset(self, id, size):
        if self.fail_download:
            raise OSError("download failed")
        response = self.client.get("/api/device/assets/" + id, headers=self.headers)
        assert response.status_code == 200
        return response.content

    def motion(self, sample):
        response = self.client.post("/api/device/motion", json={"sample": sample}, headers=self.headers)
        assert response.status_code == 200, response.text
        return response.json()


def test_end_to_end_sync_offline_commands_and_integrity_after_restart(setup, tmp_path):
    app, client, config = setup
    group = app.state.db.all("group")[0]
    (config.nas_root / group["folder"] / "Foto.jpg").write_bytes(image_bytes())
    app.state.media.scan()
    device, auth = pair_device(client, group)
    transport = LocalAPI(client, auth)
    cfg = {"cache_dir": str(tmp_path / "player")}
    worker = SyncWorker(cfg, api=transport)
    worker.sync_once()
    cached = worker.snapshot()
    transport.offline = True
    with pytest.raises(OSError):
        worker.sync_once()
    assert SyncWorker(cfg, api=transport).snapshot() == cached
    transport.offline = False
    worker.cache.path(cached["photos"][0]).write_bytes(b"corrupt")
    restarted = SyncWorker(cfg, api=transport)
    restarted.sync_once()
    assert (
        hashlib.sha256(restarted.cache.path(cached["photos"][0]).read_bytes()).hexdigest()
        == cached["photos"][0]
    )
    command = client.post(f"/api/admin/devices/{device['id']}/commands/restart").json()["id"]
    restarted.sync_once()
    assert restarted.restart.is_set()
    assert command in json.loads(restarted.state_path.read_text())["ack"]
    after_restart = SyncWorker(cfg, api=transport)
    after_restart.sync_once()
    assert not after_restart.restart.is_set()
    assert client.post("/api/device/sync", json={}, headers=auth).json()["commands"] == []


def test_permission_revocation_clears_old_cache_before_failed_download(setup, tmp_path):
    app, client, config = setup
    group, other = app.state.db.all("group")[:2]
    for g, color in [(group, "red"), (other, "blue")]:
        (config.nas_root / g["folder"] / "photo.jpg").write_bytes(image_bytes(color))
    app.state.media.scan()
    device, auth = pair_device(client, group, internal=True)
    transport = LocalAPI(client, auth)
    worker = SyncWorker({"cache_dir": str(tmp_path / "player")}, api=transport)
    worker.sync_once()
    client.put(
        "/api/admin/devices/" + device["id"],
        json={"name": device["name"], "group_id": other["id"], "allow_internal": False},
    )
    transport.fail_download = True
    with pytest.raises(OSError):
        worker.sync_once()
    assert worker.snapshot() is None
    assert list(worker.cache.assets.iterdir()) == []
