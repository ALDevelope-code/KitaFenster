import copy

from conftest import image_bytes, pair_device, sync
from test_display_windows import upload
from test_player import LocalAPI

from player.client import SyncWorker
from server.documents import migrate_document_lists
from shared.schedule import resolve, slides


def put_list(client, document, groups=(), all_groups=False):
    response = client.put(
        f"/api/admin/documents/{document['id']}/list",
        json={
            "all_groups": all_groups,
            "group_ids": [g["id"] for g in groups],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_multiple_documents_audiences_future_groups_and_secondary_mixed(setup):
    app, client, _ = setup
    groups = app.state.db.all("group")
    first, second, internal = (
        upload(client, "A", "red"),
        upload(client, "B", "blue"),
        upload(client, "C", "green"),
    )
    client.put(
        f"/api/admin/documents/{internal['id']}",
        json={"name": "Internal", "category": "Dokument", "public": False},
    )
    put_list(client, first, all_groups=True)
    put_list(client, second, groups[:1])
    put_list(client, internal, all_groups=True)
    settings = {
        "split": {
            "enabled": True,
            "secondary": {
                "default_mode": "mixed",
                "playlist": [
                    {"mode": "messages", "seconds": 9},
                    {"mode": "plan", "seconds": 7},
                ],
            },
        }
    }
    client.put("/api/admin/notices/new", json={"title": "Hallo"})
    device, auth = pair_device(client, groups[0], settings=settings)
    m = sync(client, auth)["manifest"]
    assert m["plan"] == first["assets"] + second["assets"]
    assert all(a in m["assets"] for a in m["plan"])
    assert not set(internal["assets"]) & m["assets"].keys()
    result = slides(m, resolve(m)["secondary"])
    assert [(s["kind"], s["seconds"]) for s in result] == [("notice", 9), ("image", 7), ("image", 7)]
    preview = client.get(f"/api/admin/preview/{device['id']}").json()
    assert preview["secondary_slides"] == result
    future = client.post("/api/admin/groups", json={"name": "Neue Gruppe", "folder": "Neu"}).json()
    _, future_auth = pair_device(client, future)
    assert sync(client, future_auth)["manifest"]["plan"] == first["assets"]
    _, staff_auth = pair_device(client, groups[0], internal=True)
    assert (
        sync(client, staff_auth)["manifest"]["plan"]
        == first["assets"] + second["assets"] + internal["assets"]
    )
    put_list(client, first)
    assert sync(client, auth)["manifest"]["plan"] == second["assets"]
    assert app.state.db.get("document", first["id"])


def test_list_cache_revocation_and_document_deletion(setup, tmp_path):
    app, client, _ = setup
    group = app.state.db.all("group")[0]
    doc = upload(client)
    put_list(client, doc, all_groups=True)
    _, auth = pair_device(client, group, settings={"default_mode": "plan"})
    transport = LocalAPI(client, auth)
    cfg = {"cache_dir": str(tmp_path / "player")}
    worker = SyncWorker(cfg, api=transport)
    worker.sync_once()
    transport.offline = True
    offline = SyncWorker(cfg, api=transport)
    assert slides(offline.snapshot(), resolve(offline.snapshot()))[0]["asset"] == doc["assets"][0]
    put_list(client, doc)
    transport.offline = False
    offline.sync_once()
    assert offline.snapshot()["plan"] == []
    assert not offline.cache.path(doc["assets"][0]).exists()
    put_list(client, doc, all_groups=True)
    path = f"/api/admin/documents/{doc['id']}"
    assert client.delete(path).status_code == 409
    usage = client.get(path + "/usage").json()
    assert any(r["kind"] == "document_list" for r in usage["references"])
    assert client.delete(path, params={"unlink": True, "revision": usage["revision"]}).status_code == 200
    assert sync(client, auth)["manifest"]["plan"] == []


def test_migration_preserves_existing_group_permissions_and_is_idempotent(setup):
    app, client, _ = setup
    db = app.state.db
    first, second = db.all("group")[:2]
    doc = upload(client)
    db.mutate("document", doc["id"], {"public": False})
    for group, public in [(first, True), (second, False)]:
        client.put(f"/api/admin/groups/{group['id']}/plan/{doc['id']}", json={"plan_public": public})
    _, auth1 = pair_device(client, first)
    _, auth2 = pair_device(client, second)
    before = [sync(client, auth)["manifest"]["plan"] for auth in (auth1, auth2)]
    migrate_document_lists(db)
    migrated = copy.deepcopy(db.all("document"))
    migrate_document_lists(db)
    assert db.all("document") == migrated
    assert all(db.get("group", g["id"])["plan_id"] is None for g in (first, second))
    assert [sync(client, auth)["manifest"]["plan"] for auth in (auth1, auth2)] == before
    client.put(
        f"/api/admin/documents/{doc['id']}",
        json={
            "name": "Internal",
            "category": "Dokument",
            "public": False,
            "revoke_group_release": True,
        },
    )
    assert sync(client, auth1)["manifest"]["plan"] == []


def test_legacy_nas_becomes_manageable_list_document_and_keeps_refreshing(setup):
    app, client, config = setup
    db = app.state.db
    group = db.all("group")[0]
    source = config.nas_root / group["folder"] / "Plan.jpg"
    source.write_bytes(image_bytes())
    db.mutate("group", group["id"], {"plan_path": "Plan.jpg", "plan_public": True})
    app.state.media.scan()
    _, auth = pair_device(client, group)
    before = sync(client, auth)["manifest"]["plan"]
    migrate_document_lists(db)
    imported = db.get("document", "nas-" + group["id"])
    assert imported["assets"] == before
    assert sync(client, auth)["manifest"]["plan"] == before
    source.write_bytes(image_bytes("blue"))
    app.state.media.scan()
    assert sync(client, auth)["manifest"]["plan"] != before
    # Editing only name and photo folder must not silently discard an imported source.
    client.put(f"/api/admin/groups/{group['id']}", json={"name": "Piraten", "folder": group["folder"]})
    assert db.get("group", group["id"])["plan_path"] == "Plan.jpg"
    put_list(client, imported)
    assert sync(client, auth)["manifest"]["plan"] == []
    assert source.is_file()


def test_list_validation_and_access_checks(setup):
    app, client, _ = setup
    doc = upload(client)
    path = f"/api/admin/documents/{doc['id']}/list"
    assert client.put(path, json={"group_ids": ["missing"]}).status_code == 404
    assert "list_assignment" not in app.state.db.get("document", doc["id"])
    image = client.post("/api/admin/upload/image", files={"file": ("Image.jpg", image_bytes())}).json()
    assert (
        client.put(f"/api/admin/documents/{image['id']}/list", json={"all_groups": True}).status_code == 422
    )
    del client.headers["X-CSRF-Token"]
    assert client.put(path, json={"all_groups": True}).status_code == 403
    client.cookies.clear()
    assert client.put(path, json={"all_groups": True}).status_code == 401
