"""Regressionen für Rechte, Anmeldung und den lokalen Display-Cache."""

import hashlib

import pytest
from conftest import image_bytes, pair_device, sync
from fastapi.testclient import TestClient

from player.cache import Cache
from player.client import SyncWorker
from server.security import secure_equals


def test_login_counts_failures_only_and_handles_unicode(setup):
    _, client, _ = setup
    for _ in range(12):
        assert (
            client.post(
                "/api/login", json={"username": "admin", "password": "Nur-fuer-Tests-123!"}
            ).status_code
            == 200
        )
    assert secure_equals("\ud800", "admin") is False
    assert client.post("/api/login", json={"username": "ä", "password": "falsch"}).status_code == 401
    for _ in range(9):
        assert client.post("/api/login", json={"username": "admin", "password": "falsch"}).status_code == 401
    assert client.post("/api/login", json={"username": "admin", "password": "falsch"}).status_code == 429


def test_login_lone_surrogates_are_rejected_without_server_error(setup):
    app, _, _ = setup
    with TestClient(app, raise_server_exceptions=False) as client:
        for payload, expected in (
            (b'{"username":"\\ud800","password":"falsch"}', 422),
            (b'{"username":"admin","password":"\\ud800"}', 401),
        ):
            response = client.post(
                "/api/login", content=payload, headers={"content-type": "application/json"}
            )
            assert response.status_code == expected


def test_pairing_success_after_failures_and_code_length(setup):
    app, client, _ = setup
    group = app.state.db.all("group")[0]
    for _ in range(10):
        assert client.post("/api/device/pair", json={"code": "000000"}).status_code == 401
    response = client.post(
        "/api/admin/devices", json={"name": "Rahmen", "group_id": group["id"], "allow_internal": False}
    )
    assert response.status_code == 200
    code = response.json()["code"]
    assert len(code) == 16
    assert client.post("/api/device/pair", json={"code": code}).status_code == 200


def test_nas_plan_download_and_unassigned_document_remain_scoped(setup):
    app, client, config = setup
    group = app.state.db.all("group")[0]
    folder = config.nas_root / group["folder"]
    (folder / "Plan.jpg").write_bytes(image_bytes())
    app.state.db.mutate("group", group["id"], {"plan_path": "Plan.jpg", "plan_public": True})
    app.state.media.scan()
    _, auth = pair_device(client, group)
    manifest = sync(client, auth)["manifest"]
    assert manifest["plan"]
    assert client.get("/api/device/assets/" + manifest["plan"][0], headers=auth).status_code == 200

    document = client.post(
        "/api/admin/upload/plan", files={"file": ("Extra.jpg", image_bytes("blue"), "image/jpeg")}
    ).json()
    client.put(
        f"/api/admin/documents/{document['id']}",
        json={"name": "Extra", "category": "Dokument", "public": True},
    )
    assert document["assets"][0] not in sync(client, auth)["manifest"]["assets"]
    assert client.get("/api/device/assets/" + document["assets"][0], headers=auth).status_code == 404


def test_document_rename_preserves_group_release_but_explicit_revocation_removes_it(setup):
    app, client, _ = setup
    group = app.state.db.all("group")[0]
    document = client.post(
        "/api/admin/upload/plan", files={"file": ("Plan.jpg", image_bytes(), "image/jpeg")}
    ).json()
    client.put(f"/api/admin/groups/{group['id']}/plan/{document['id']}", json={"plan_public": True})
    _, auth = pair_device(client, group)
    assert sync(client, auth)["manifest"]["plan"] == document["assets"]
    response = client.put(
        f"/api/admin/documents/{document['id']}",
        json={
            "name": "Neuer Name",
            "category": "Dokument",
            "public": False,
        },
    )
    assert response.status_code == 200
    assert sync(client, auth)["manifest"]["plan"] == document["assets"]
    client.put(
        f"/api/admin/documents/{document['id']}",
        json={
            "name": "Neuer Name",
            "category": "Dokument",
            "public": False,
            "revoke_group_release": True,
        },
    )
    assert sync(client, auth)["manifest"]["plan"] == []


def test_revoking_a_document_does_not_change_an_independent_nas_plan_release(setup):
    app, client, _ = setup
    db = app.state.db
    group = db.all("group")[0]
    document = client.post(
        "/api/admin/upload/plan", files={"file": ("Plan.jpg", image_bytes(), "image/jpeg")}
    ).json()
    db.mutate(
        "group",
        group["id"],
        {"plan_id": document["id"], "plan_path": "NAS-Plan.jpg", "plan_public": True},
    )
    response = client.put(
        f"/api/admin/documents/{document['id']}",
        json={"name": "Plan", "category": "Dokument", "public": False},
    )
    assert response.status_code == 200
    assert db.get("group", group["id"])["plan_public"] is True


def test_cache_partial_install_and_warning_persist(tmp_path):
    from test_player import manifest

    contents = [bytes([index]) * 600_000 for index in (1, 2)]
    ids = [hashlib.sha256(data).hexdigest() for data in contents]
    current = manifest(contents[0])
    current["photos"] = ids
    current["assets"] = {id: {"id": id, "sha256": id, "bytes": len(data)} for id, data in zip(ids, contents)}
    source = dict(zip(ids, contents))

    class API:
        def sync(self, _):
            return {"manifest": current}

        def asset(self, id, size):
            return source[id]

    worker = SyncWorker({"cache_dir": str(tmp_path), "cache_limit_mb": 1}, api=API())
    worker.sync_once()
    assert len(worker.snapshot()["photos"]) == 1
    assert len(Cache(tmp_path).load()["assets"]) == 1
    assert "1 MiB" in worker.status["error"]
    worker.sync_once()
    assert "1 MiB" in worker.status["error"]


def test_folder_change_discards_old_cache_before_failed_download(tmp_path):
    from test_player import manifest

    first, second = image_bytes(), image_bytes("blue")
    old = manifest(first)
    old["policy"]["folder"] = "old"
    new = manifest(second, "2")
    new["policy"]["folder"] = "new"
    Cache(tmp_path).install(old, lambda *_: first)

    class FailedAPI:
        def sync(self, _):
            return {"manifest": new}

        def asset(self, id, size):
            raise OSError("download failed")

    worker = SyncWorker({"cache_dir": str(tmp_path)}, api=FailedAPI())
    with pytest.raises(OSError):
        worker.sync_once()
    assert worker.snapshot() is None
    assert Cache(tmp_path).load() is None
    assert not Cache(tmp_path).path(old["photos"][0]).exists()


def test_failed_download_keeps_last_valid_files(tmp_path):
    from test_player import manifest

    first, second = image_bytes(), image_bytes("blue")
    cache = Cache(tmp_path)
    old = manifest(first)
    cache.install(old, lambda *_: first)
    with pytest.raises(OSError):
        cache.install(manifest(second, "2"), lambda *_: (_ for _ in ()).throw(OSError()))
    assert cache.load() == old
    assert cache.path(old["photos"][0]).exists()
