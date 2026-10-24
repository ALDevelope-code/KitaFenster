import pytest
from conftest import image_bytes, pair_device, sync
from test_player import LocalAPI
from test_schedule import at, base

from player.client import SyncWorker
from server.models import Settings
from shared.schedule import resolve, slides


def window(mode="photos", **values):
    return {"days": [0], "start": "07:00", "end": "18:00", "mode": mode, **values}


def test_first_matching_window_selects_content_and_reordering_changes_winner():
    m = base()
    m["documents"] = {"menu": {"assets": ["menu-page-1", "menu-page-2"]}}
    m["settings"]["content_windows"] = [
        window("plan", name="Mittagessen", start="11:00", end="13:00", document_id="menu"),
        window("photos", name="Elternzeit"),
    ]
    assert resolve(m, at("2026-09-14T06:00:00"))["mode"] == "photos"
    decision = resolve(m, at("2026-09-14T10:00:00"))
    assert decision["reason"] == "Inhaltszeitfenster 1: Mittagessen"
    assert [s["asset"] for s in slides(m, decision)] == ["menu-page-1", "menu-page-2"]
    assert resolve(m, at("2026-09-14T11:00:00"))["mode"] == "photos"
    m["settings"]["content_windows"].reverse()
    assert resolve(m, at("2026-09-14T10:00:00"))["mode"] == "photos"
    assert resolve(m, at("2026-09-14T16:00:00"))["mode"] == "photos"


def test_pausing_times_keeps_rules_but_uses_default_and_preserves_overrides():
    m = base()
    m["settings"].update(content_windows=[window("plan")], content_windows_enabled=False)
    assert resolve(m, at("2026-09-14T10:00:00"))["reason"] == "Standardanzeige"
    assert resolve(m, at("2026-09-14T22:00:00"))["mode"] == "photos"
    m["manual"] = {"mode": "mixed"}
    assert resolve(m, at("2026-09-14T22:00:00"))["mode"] == "mixed"
    m["notices"] = [{"id": "urgent", "urgent": True}]
    assert resolve(m, at("2026-09-14T22:00:00"))["reason"] == "Sofortmeldung"
    m.update(manual=None, notices=[])
    m["settings"]["content_windows_enabled"] = True
    assert resolve(m, at("2026-09-14T10:00:00"))["mode"] == "plan"
    assert resolve(m, at("2026-09-14T22:00:00"))["mode"] == "photos"


def test_standard_content_in_top_window_overrides_lower_windows():
    m = base()
    m["settings"]["default_mode"] = "messages"
    m["settings"]["content_windows"] = [window(None), window("photos")]
    assert resolve(m, at("2026-09-14T10:00:00"))["mode"] == "messages"


def test_window_selection_across_midnight_and_repeated_dst_hour():
    m = base()
    m["settings"]["content_windows"] = [window("plan", start="22:00", end="02:00")]
    assert resolve(m, at("2026-09-14T23:00:00"))["mode"] == "plan"
    assert resolve(m, at("2026-09-15T00:00:00"))["mode"] == "photos"
    m["settings"]["content_windows"] = [window("messages", days=[6], start="02:00", end="03:00")]
    assert resolve(m, at("2026-10-25T00:30:00"))["mode"] == "messages"
    assert resolve(m, at("2026-10-25T01:30:00"))["mode"] == "messages"


def upload(client, name="Speiseplan", color="blue", public=True):
    response = client.post(
        "/api/admin/upload/plan",
        data={"category": name, "public": str(public).lower()},
        files={"file": (name + ".jpg", image_bytes(color), "image/jpeg")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_document_metadata_selected_pages_and_offline_switching(setup, tmp_path):
    app, client, config = setup
    group = app.state.db.all("group")[0]
    (config.nas_root / group["folder"] / "Foto.jpg").write_bytes(image_bytes("red"))
    app.state.media.scan()
    menu = upload(client)
    info = upload(client, "Elterninformation", "green")
    hours = [window("plan", start="11:00", end="13:00", document_id=menu["id"]), window("photos")]
    device, auth = pair_device(
        client,
        group,
        settings={
            "default_mode": "plan",
            "document_id": info["id"],
            "content_windows": hours,
        },
    )
    transport = LocalAPI(client, auth)
    cfg = {"cache_dir": str(tmp_path / "pi")}
    worker = SyncWorker(cfg, api=transport)
    worker.sync_once()
    cached = worker.snapshot()
    preview = client.get(f"/api/admin/preview/{device['id']}", params={"at": "2026-09-14T10:00:00Z"}).json()
    assert preview["slides"][0]["asset"] == menu["assets"][0]
    transport.offline = True
    restarted = SyncWorker(cfg, api=transport)
    m = restarted.snapshot()
    assert m == cached
    assert slides(m, resolve(m, at("2026-09-14T10:00:00")))[0]["asset"] == menu["assets"][0]
    assert slides(m, resolve(m, at("2026-09-14T13:00:00")))[0]["asset"] == m["photos"][0]
    changed = client.put(
        "/api/admin/documents/" + menu["id"],
        json={
            "name": "Speiseplan September",
            "category": "Mittagessen",
            "public": True,
        },
    ).json()
    assert changed["category"] == "Mittagessen"
    assert changed["assets"] == menu["assets"]
    assert changed["created_at"] == menu["created_at"]
    paused = client.put(
        "/api/admin/devices/" + device["id"],
        json={
            "name": device["name"],
            "group_id": group["id"],
            "settings": {**device["settings"], "content_windows_enabled": False},
        },
    ).json()
    assert paused["settings"]["content_windows"] == device["settings"]["content_windows"]
    preview = client.get(f"/api/admin/preview/{device['id']}", params={"at": "2026-09-14T22:00:00Z"}).json()
    assert preview["slides"][0]["asset"] == info["assets"][0]
    assert client.delete("/api/admin/documents/" + menu["id"]).status_code == 409


def test_private_document_is_filtered_and_revocation_clears_cached_pages(setup, tmp_path):
    app, client, config = setup
    group = app.state.db.all("group")[0]
    menu = upload(client)
    internal = upload(client, "Personal", "green", public=False)
    device, auth = pair_device(client, group, settings={"default_mode": "plan", "document_id": menu["id"]})
    manifest = sync(client, auth)["manifest"]
    assert menu["id"] in manifest["documents"]
    assert internal["id"] not in manifest["documents"]
    assert internal["assets"][0] not in manifest["assets"]
    assert client.get("/api/device/assets/" + internal["assets"][0], headers=auth).status_code == 404
    denied = client.put(
        "/api/admin/devices/" + device["id"],
        json={
            "name": device["name"],
            "group_id": group["id"],
            "settings": {"document_id": internal["id"], "default_mode": "plan"},
        },
    )
    assert denied.status_code == 422
    assert "nur intern" in denied.text
    transport = LocalAPI(client, auth)
    worker = SyncWorker({"cache_dir": str(tmp_path / "pi")}, api=transport)
    worker.sync_once()
    client.put(
        "/api/admin/documents/" + menu["id"],
        json={
            "name": menu["name"],
            "category": menu["category"],
            "public": False,
        },
    )
    (config.nas_root / group["folder"] / "new.jpg").write_bytes(image_bytes("yellow"))
    app.state.media.scan()
    transport.fail_download = True
    with pytest.raises(OSError):
        worker.sync_once()
    assert worker.snapshot() is None
    assert not worker.cache.path(menu["assets"][0]).exists()
    assert client.get("/api/device/assets/" + menu["assets"][0], headers=auth).status_code == 404


def test_selected_missing_document_never_falls_back_to_another_plan():
    m = base()
    m["settings"].update(default_mode="plan", document_id="missing")
    assert slides(m, resolve(m)) == []
    m["documents"] = {"menu": {"assets": ["menu"]}}
    m["settings"].update(
        default_mode="mixed",
        playlist=[
            {"mode": "plan", "seconds": 20, "document_id": "menu"},
            {"mode": "plan", "seconds": 10, "document_id": None},
        ],
    )
    assert [s["asset"] for s in slides(m, resolve(m))] == ["menu", "p1", "p2"]


def test_public_document_also_works_as_group_default_and_revocation_changes_policy(setup):
    app, client, _ = setup
    group = app.state.db.all("group")[0]
    doc = upload(client)
    client.put(f"/api/admin/groups/{group['id']}/plan/{doc['id']}", json={"plan_public": False})
    _, auth = pair_device(client, group, settings={"default_mode": "plan"})
    before = sync(client, auth)["manifest"]
    assert before["plan"] == doc["assets"]
    client.put(
        "/api/admin/documents/" + doc["id"],
        json={
            "name": doc["name"],
            "category": doc["category"],
            "public": False,
        },
    )
    after = sync(client, auth)["manifest"]
    assert after["plan"] == []
    assert before["policy"] != after["policy"]


def test_group_permission_does_not_expose_upload_when_it_belongs_to_a_nas_document(setup):
    app, client, _ = setup
    group = app.state.db.all("group")[0]
    private = upload(client, public=False)
    db = app.state.db
    db.mutate(
        "group",
        group["id"],
        {
            "plan_id": private["id"],
            "plan_public": True,
            "plan_path": "Parents.pdf",
        },
    )
    device, auth = pair_device(client, group)
    db.mutate(
        "device",
        device["id"],
        {"settings": Settings(default_mode="plan", document_id=private["id"]).model_dump()},
    )
    m = sync(client, auth)["manifest"]
    assert private["id"] not in m["documents"]
    assert private["assets"][0] not in m["assets"]
    db.mutate("group", group["id"], {"plan_path": ""})
    assert private["id"] in sync(client, auth)["manifest"]["documents"]


def test_document_edit_validates_metadata_and_requires_csrf(setup):
    _, client, _ = setup
    doc = upload(client)
    url = "/api/admin/documents/" + doc["id"]
    for category in [" ", "x" * 61, "bad\nvalue"]:
        assert client.put(url, json={"name": doc["name"], "category": category}).status_code == 422
    assert client.put(url, json={"name": doc["name"], "category": "Okay", "kind": "image"}).status_code == 422
    del client.headers["X-CSRF-Token"]
    assert client.put(url, json={"name": doc["name"], "category": "Okay"}).status_code == 403


@pytest.mark.parametrize(
    "change",
    [
        {"content_windows_enabled": "maybe"},
        {"content_windows": [window("invalid")]},
        {"content_windows": [window(start="25:00")]},
        {"content_windows": [window(days=[])]},
    ],
)
def test_invalid_time_configuration_is_rejected(setup, change):
    app, client, _ = setup
    response = client.post(
        "/api/admin/devices",
        json={
            "name": "Test",
            "group_id": app.state.db.all("group")[0]["id"],
            "settings": change,
        },
    )
    assert response.status_code == 422
