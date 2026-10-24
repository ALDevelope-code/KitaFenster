import hashlib
from collections import namedtuple

from conftest import pair_device
from test_player import LocalAPI, manifest

from player.cache import Cache
from player.client import SyncWorker


def test_disk_reserve_limits_new_downloads_without_discarding_cached_images(tmp_path, monkeypatch):
    images = [bytes([index]) * 600_000 for index in (1, 2)]
    ids = [hashlib.sha256(image).hexdigest() for image in images]
    current = manifest(images[0])
    current["photos"] = ids
    current["assets"] = {id: {"id": id, "sha256": id, "bytes": len(image)} for id, image in zip(ids, images)}
    volume = namedtuple("Volume", "total used free")
    total = 100 * 1024 * 1024
    reserve = total // 10
    free = reserve + 32 * 1024 * 1024 + 800_000
    monkeypatch.setattr("player.cache.shutil.disk_usage", lambda _: volume(total, total - free, free))

    cache = Cache(tmp_path)
    stored, missing = cache.install(current, lambda id, _: dict(zip(ids, images))[id])
    assert stored["photos"] == ids[:1]
    assert missing == 600_000
    assert cache.disk_missing_bytes == 600_000
    assert cache.storage()["reserved_bytes"] == reserve

    free = reserve - 1
    stored, missing = cache.install(current, lambda *_: (_ for _ in ()).throw(AssertionError()))
    assert stored["photos"] == ids[:1]
    assert missing == 600_000
    assert cache.path(ids[0]).exists()


def test_storage_is_reported_to_admin_after_capability_handshake(setup, tmp_path):
    app, client, _ = setup
    group = app.state.db.all("group")[0]
    device, auth = pair_device(client, group)
    worker = SyncWorker({"cache_dir": str(tmp_path)}, api=LocalAPI(client, auth))
    worker.sync_once()
    assert app.state.db.get("device", device["id"])["reported"]["storage"] is None
    worker.sync_once()
    storage = app.state.db.get("device", device["id"])["reported"]["storage"]
    assert storage["total_bytes"] > 0
    assert 0 <= storage["free_bytes"] <= storage["total_bytes"]
    assert storage["reserved_bytes"] >= storage["total_bytes"] // 10
    shown = next(d for d in client.get("/api/admin/state").json()["devices"] if d["id"] == device["id"])
    assert shown["reported"]["storage"] == storage


def test_player_fetches_omitted_images_when_free_space_returns(tmp_path, monkeypatch):
    images = [bytes([index]) * 600_000 for index in (3, 4)]
    ids = [hashlib.sha256(image).hexdigest() for image in images]
    current = manifest(images[0])
    current["photos"] = ids
    current["assets"] = {id: {"id": id, "sha256": id, "bytes": len(image)} for id, image in zip(ids, images)}
    source = dict(zip(ids, images))
    volume = namedtuple("Volume", "total used free")
    total = 100 * 1024 * 1024
    minimum = total // 10 + 32 * 1024 * 1024
    free = minimum + 800_000
    monkeypatch.setattr("player.cache.shutil.disk_usage", lambda _: volume(total, total - free, free))

    class API:
        def sync(self, _):
            return {"manifest": current}

        def asset(self, id, size):
            return source[id]

    worker = SyncWorker({"cache_dir": str(tmp_path), "cache_limit_mb": 2}, api=API())
    worker.sync_once()
    assert worker.snapshot()["photos"] == ids[:1]
    free = minimum + 1_300_000
    worker.sync_once()
    assert worker.snapshot()["photos"] == ids
    assert worker.status["error"] == ""


def test_new_player_omits_storage_fields_for_older_server(tmp_path):
    data = b"image"
    current = manifest(data)

    class OldAPI:
        def __init__(self):
            self.states = []

        def sync(self, state):
            self.states.append(state)
            return {"manifest": current}

        def asset(self, *_):
            return data

    api = OldAPI()
    worker = SyncWorker({"cache_dir": str(tmp_path)}, api=api)
    worker.sync_once()
    worker.sync_once()
    assert all("storage" not in state for state in api.states)
