import io
import os
import time
import zipfile

import pytest
from conftest import image_bytes, pair_device, sync
from fastapi.testclient import TestClient
from PIL import Image

from server.media import within
from server.models import Settings


def test_login_csrf_and_secret_separation(setup):
    app, client, _ = setup
    with TestClient(app) as stranger:
        assert stranger.get("/api/admin/state").status_code == 401
        assert (
            stranger.post("/api/login", json={"username": "admin", "password": "falsch"}).status_code == 401
        )
        assert stranger.get("/api/device/assets/" + "a" * 64).status_code == 401
    assert client.post("/api/admin/scan", headers={"X-CSRF-Token": "wrong"}).status_code == 403
    group = client.get("/api/admin/state").json()["groups"][0]
    _, headers = pair_device(client, group)
    content = client.get("/api/admin/state").text
    assert headers["Authorization"][7:] not in content
    assert "Nur-fuer-Tests" not in content
    assert client.get("/").headers["content-security-policy"]
    assert client.get("/").headers["cache-control"] == "no-cache"
    assert client.get("/static/split-display.js").headers["cache-control"] == "no-cache"


def test_nas_add_change_delete_and_outage(setup):
    app, client, config = setup
    group = app.state.db.all("group")[0]
    photo = config.nas_root / group["folder"] / "Foto.jpg"
    photo.write_bytes(image_bytes())
    device, headers = pair_device(client, group)
    app.state.media.scan()
    first = sync(client, headers)["manifest"]
    assert len(first["photos"]) == 1
    photo.write_bytes(image_bytes("blue"))
    app.state.media.scan()
    second = sync(client, headers)["manifest"]
    assert second["photos"] != first["photos"]
    marker = config.nas_root / ".bilderrahmen-source"
    marker.unlink()
    photo.unlink()
    app.state.media.scan()
    outage = sync(client, headers)
    assert outage["manifest"]["photos"] == second["photos"]
    assert outage["nas_error"]
    marker.touch()
    app.state.media.scan()
    empty = sync(client, headers)["manifest"]
    assert empty["photos"] == []
    assert client.get("/api/device/assets/" + second["photos"][0], headers=headers).status_code == 404


def test_unreadable_file_preserves_whole_group_snapshot(setup):
    app, _, config = setup
    group = app.state.db.all("group")[0]
    folder = config.nas_root / group["folder"]
    (folder / "a.jpg").write_bytes(image_bytes())
    app.state.media.scan()
    before = app.state.db.get("snapshot", group["id"])
    (folder / "b.jpg").write_bytes(b"incomplete upload")
    app.state.media.scan()
    after = app.state.db.get("snapshot", group["id"])
    assert before["photos"] == after["photos"]
    assert after["error"]
    (folder / "b.jpg").write_bytes(image_bytes("green"))
    app.state.media.scan()
    assert len(app.state.db.get("snapshot", group["id"])["photos"]) == 2


def test_group_isolation_and_pair_code_single_use(setup):
    app, client, config = setup
    a, b = app.state.db.all("group")[:2]
    (config.nas_root / a["folder"] / "a.jpg").write_bytes(image_bytes())
    (config.nas_root / b["folder"] / "b.jpg").write_bytes(image_bytes("blue"))
    app.state.media.scan()
    device_a, auth_a = pair_device(client, a)
    _, auth_b = pair_device(client, b)
    a_id = sync(client, auth_a)["manifest"]["photos"][0]
    assert client.get("/api/device/assets/" + a_id, headers=auth_b).status_code == 404
    assert client.get("/api/device/assets/" + a_id, headers=auth_a).status_code == 200
    code = client.post(f"/api/admin/devices/{device_a['id']}/pair").json()["code"]
    assert client.post("/api/device/pair", json={"code": code}).status_code == 200
    assert client.post("/api/device/pair", json={"code": code}).status_code == 401
    assert client.post("/api/device/sync", json={}, headers=auth_a).status_code == 401


def test_internal_notices_and_plans_never_reach_parent_player(setup):
    app, client, _ = setup
    group = app.state.db.all("group")[0]
    _, parent = pair_device(client, group)
    _, internal = pair_device(client, group, internal=True)
    plan = client.post(
        "/api/admin/upload/plan", files={"file": ("Plan.jpg", image_bytes(), "image/jpeg")}
    ).json()
    client.put(f"/api/admin/groups/{group['id']}/plan/{plan['id']}")
    notice = client.put(
        "/api/admin/notices/new",
        json={"title": "Intern", "text": "Nur Personal", "internal": True, "urgent": True},
    ).json()
    public = sync(client, parent)["manifest"]
    staff = sync(client, internal)["manifest"]
    assert public["plan"] == [] and public["notices"] == [] and public["assets"] == {}
    assert staff["plan"] == plan["assets"]
    assert staff["notices"][0]["id"] == notice["id"]
    assert client.get("/api/device/assets/" + plan["assets"][0], headers=parent).status_code == 404
    client.put(
        "/api/admin/groups/" + group["id"],
        json={"name": group["name"], "folder": group["folder"], "plan_public": True},
    )
    assert sync(client, parent)["manifest"]["plan"] == plan["assets"]
    assert sync(client, parent)["manifest"]["notices"] == []


def test_nas_plan_image_excluded_from_slideshow(setup):
    app, client, config = setup
    group = app.state.db.all("group")[0]
    folder = config.nas_root / group["folder"]
    (folder / "Plan.jpg").write_bytes(image_bytes("green"))
    (folder / "Foto.jpg").write_bytes(image_bytes("blue"))
    result = client.put(
        "/api/admin/groups/" + group["id"],
        json={"name": group["name"], "folder": group["folder"], "plan_path": "Plan.jpg"},
    )
    assert result.status_code == 200
    app.state.media.scan()
    snap = app.state.db.get("snapshot", group["id"])
    assert len(snap["photos"]) == 1 and len(snap["plan"]) == 1
    assert snap["photos"] != snap["plan"]


def asset_names(config):
    return {path.name for path in (config.data_dir / "assets").iterdir()}


def backdate(config, asset_id, media):
    path = config.data_dir / "assets" / (asset_id + ".jpg")
    stale_ns = int((time.time() - media.sweep_grace_seconds - 60) * 1_000_000_000)
    os.utime(path, ns=(stale_ns, stale_ns))


def test_deleted_nas_photo_releases_its_prepared_asset(setup):
    app, _, config = setup
    db = app.state.db
    group = db.all("group")[0]
    folder = config.nas_root / group["folder"]
    (folder / "a.jpg").write_bytes(image_bytes())
    (folder / "b.jpg").write_bytes(image_bytes("blue"))
    app.state.media.scan()
    first = db.get("snapshot", group["id"])
    assert len(first["photos"]) == 2
    dropped, kept = first["photos"][:1], first["photos"][1:]
    (folder / "a.jpg").unlink()
    # The asset is protected by the grace period until it is older than five minutes.
    backdate(config, dropped[0], app.state.media)
    app.state.media.scan()
    second = db.get("snapshot", group["id"])
    assert second["photos"] == kept
    assert asset_names(config) == {item + ".jpg" for item in kept}
    assert db.get("asset", dropped[0]) is None
    # Re-adding the same file renders it again (the source row is gone) and nothing else.
    (folder / "a.jpg").write_bytes(image_bytes())
    app.state.media.scan()
    again = db.get("snapshot", group["id"])
    assert again["photos"] == first["photos"]
    assert asset_names(config) == {item + ".jpg" for item in first["photos"]}


def test_document_delete_releases_unused_assets(setup):
    app, client, config = setup
    db = app.state.db
    group = db.all("group")[0]
    used = client.post(
        "/api/admin/upload/plan", files={"file": ("Geplant.jpg", image_bytes("green"), "image/jpeg")}
    ).json()
    unused = client.post(
        "/api/admin/upload/plan", files={"file": ("Ungenutzt.jpg", image_bytes("blue"), "image/jpeg")}
    ).json()
    db.mutate("group", group["id"], {"plan_id": used["id"]})
    db.delete("document", unused["id"])
    backdate(config, used["assets"][0], app.state.media)
    backdate(config, unused["assets"][0], app.state.media)
    (config.nas_root / group["folder"] / "Foto.jpg").write_bytes(image_bytes("red"))
    app.state.media.scan()
    files = asset_names(config)
    assert used["assets"][0] + ".jpg" in files
    assert unused["assets"][0] + ".jpg" not in files
    assert db.get("document", used["id"])["assets"] == used["assets"]
    assert db.get("asset", unused["assets"][0]) is None


def test_shared_and_new_assets_survive_the_sweep(setup):
    app, client, config = setup
    db = app.state.db
    group = db.all("group")[0]
    (config.nas_root / group["folder"] / "Foto.jpg").write_bytes(image_bytes())
    app.state.media.scan()
    photo = db.get("snapshot", group["id"])["photos"][0]
    # Two uploads of identical content yield the same content-addressed asset.
    used = client.post("/api/admin/upload/image", files={"file": ("a.jpg", image_bytes())}).json()
    shared = client.post("/api/admin/upload/image", files={"file": ("b.jpg", image_bytes())}).json()
    assert used["assets"] == shared["assets"] == [photo]
    db.delete("document", used["id"])
    backdate(config, photo, app.state.media)
    app.state.media.sweep()
    # Both documents shared the asset; deleting one must keep the other.
    assert db.get("document", shared["id"]) is not None
    assert (config.data_dir / "assets" / (photo + ".jpg")).exists()


def test_backup_contains_only_referenced_assets(setup, tmp_path):
    app, client, config = setup
    db = app.state.db
    group = db.all("group")[0]
    (config.nas_root / group["folder"] / "Foto.jpg").write_bytes(image_bytes())
    app.state.media.scan()
    photo = db.get("snapshot", group["id"])["photos"][0]
    orphan = client.post("/api/admin/upload/image", files={"file": ("o.jpg", image_bytes("yellow"))}).json()
    db.delete("document", orphan["id"])
    backdate(config, orphan["assets"][0], app.state.media)
    app.state.media.sweep()
    from server.manage import backup

    archive = backup(config, tmp_path / "gc.zip")
    assert (config.data_dir / "assets" / (photo + ".jpg")).exists()
    with zipfile.ZipFile(archive) as zip_file:
        names = zip_file.namelist()
        assert "assets/" + photo + ".jpg" in names
        assert "assets/" + orphan["assets"][0] + ".jpg" not in names


def test_sweep_removes_only_unreferenced_orphans(setup):
    app, _, config = setup
    keep_id, drop_id = "a" * 64, "b" * 64
    db = app.state.db
    for asset_id in (keep_id, drop_id):
        (config.data_dir / "assets" / (asset_id + ".jpg")).write_bytes(image_bytes())
        db.put(
            "asset",
            {"id": asset_id, "sha256": asset_id, "bytes": 1, "width": 1, "height": 1},
        )
        backdate(config, asset_id, app.state.media)
    db.put("document", {"id": "doc", "name": "doc", "kind": "plan", "assets": [keep_id], "public": False})
    app.state.media.sweep()
    assert (config.data_dir / "assets" / (keep_id + ".jpg")).exists()
    assert not (config.data_dir / "assets" / (drop_id + ".jpg")).exists()
    assert db.get("asset", keep_id) is not None
    assert db.get("asset", drop_id) is None


def test_fresh_orphan_survives_grace_period(setup):
    app, _, config = setup
    orphan_id = "c" * 64
    (config.data_dir / "assets" / (orphan_id + ".jpg")).write_bytes(image_bytes())
    app.state.media.sweep()
    assert (config.data_dir / "assets" / (orphan_id + ".jpg")).exists()


def with_ingest_counter(media):
    counts = {"n": 0}
    original = media.ingest

    def counting(data, suffix):
        counts["n"] += 1
        return original(data, suffix)

    media.ingest = counting
    return counts


def test_unchanged_nas_files_are_not_reread(setup):
    app, _, config = setup
    group = app.state.db.all("group")[0]
    folder = config.nas_root / group["folder"]
    (folder / "erste.jpg").write_bytes(image_bytes())
    (folder / "zweite.jpg").write_bytes(image_bytes("blue"))
    counts = with_ingest_counter(app.state.media)
    app.state.media.scan()
    first = app.state.db.get("snapshot", group["id"])
    assert counts["n"] == 2
    app.state.media.scan()
    second = app.state.db.get("snapshot", group["id"])
    assert counts["n"] == 2
    assert second["photos"] == first["photos"] and second["error"] == ""
    entries = {entry["path"]: entry for entry in second["photo_entries"]}
    assert set(entries) == {"erste.jpg", "zweite.jpg"}
    assert all(len(entry["head"]) == 64 and entry["mtime"] and entry["size"] for entry in entries.values())
    assert second["plan_sign"] is None


def test_nas_content_change_is_reingested(setup):
    app, _, config = setup
    group = app.state.db.all("group")[0]
    photo = config.nas_root / group["folder"] / "foto.jpg"
    photo.write_bytes(image_bytes())
    counts = with_ingest_counter(app.state.media)
    app.state.media.scan()
    first = app.state.db.get("snapshot", group["id"])
    assert counts["n"] == 1
    photo.write_bytes(image_bytes("blue"))
    app.state.media.scan()
    second = app.state.db.get("snapshot", group["id"])
    assert counts["n"] == 2
    assert second["photos"] != first["photos"]


def test_head_mismatch_forces_reread(setup):
    app, _, config = setup
    group = app.state.db.all("group")[0]
    photo = config.nas_root / group["folder"] / "foto.jpg"
    photo.write_bytes(image_bytes())
    counts = with_ingest_counter(app.state.media)
    app.state.media.scan()
    snapshot = app.state.db.get("snapshot", group["id"])
    snapshot["photo_entries"][0]["head"] = "0" * 64
    app.state.db.put("snapshot", snapshot)
    app.state.media.scan()
    fresh = app.state.db.get("snapshot", group["id"])
    assert counts["n"] == 2
    assert len(fresh["photo_entries"][0]["head"]) == 64
    app.state.media.scan()
    assert counts["n"] == 2


def test_outdated_snapshot_format_triggers_full_rescan(setup):
    app, _, config = setup
    group = app.state.db.all("group")[0]
    folder = config.nas_root / group["folder"]
    (folder / "erste.jpg").write_bytes(image_bytes())
    (folder / "zweite.jpg").write_bytes(image_bytes("blue"))
    counts = with_ingest_counter(app.state.media)
    app.state.media.scan()
    assert counts["n"] == 2
    snapshot = app.state.db.get("snapshot", group["id"])
    legacy = {key: value for key, value in snapshot.items() if key not in ("photo_entries", "plan_sign")}
    app.state.db.put("snapshot", legacy)
    app.state.media.scan()
    assert counts["n"] == 4
    assert len(app.state.db.get("snapshot", group["id"])["photo_entries"]) == 2


def test_unchanged_nas_plan_is_not_reread(setup):
    app, client, config = setup
    group = app.state.db.all("group")[0]
    folder = config.nas_root / group["folder"]
    (folder / "Plan.jpg").write_bytes(image_bytes("green"))
    (folder / "Foto.jpg").write_bytes(image_bytes("blue"))
    client.put(
        "/api/admin/groups/" + group["id"],
        json={"name": group["name"], "folder": group["folder"], "plan_path": "Plan.jpg"},
    )
    counts = with_ingest_counter(app.state.media)
    app.state.media.scan()
    first = app.state.db.get("snapshot", group["id"])
    assert counts["n"] == 2
    app.state.media.scan()
    second = app.state.db.get("snapshot", group["id"])
    assert counts["n"] == 2
    assert second["plan"] == first["plan"] and second["plan_sign"]["head"]
    (folder / "Plan.jpg").write_bytes(image_bytes("red"))
    app.state.media.scan()
    changed = app.state.db.get("snapshot", group["id"])
    assert counts["n"] == 3 and changed["plan"] != first["plan"]
    client.put(
        "/api/admin/groups/" + group["id"],
        json={"name": group["name"], "folder": group["folder"], "plan_path": ""},
    )
    app.state.media.scan()
    without_plan = app.state.db.get("snapshot", group["id"])
    # Changing the source set forces a full re-verification: both files are photos now.
    assert counts["n"] == 5
    assert without_plan["plan"] == [] and without_plan["plan_sign"] is None
    assert len(without_plan["photos"]) == 2


def test_pdf_pages_and_resize(setup):
    app, client, _ = setup
    buffer = io.BytesIO()
    Image.new("RGB", (500, 700), "white").save(
        buffer, "PDF", save_all=True, append_images=[Image.new("RGB", (500, 700), "blue")]
    )
    response = client.post(
        "/api/admin/upload/plan", files={"file": ("Zwei-Seiten.pdf", buffer.getvalue(), "application/pdf")}
    )
    assert response.status_code == 200, response.text
    assert len(response.json()["assets"]) == 2
    ids = app.state.media.ingest(image_bytes(size=(4000, 2000)), ".jpg")
    asset = app.state.db.get("asset", ids[0])
    assert (asset["width"], asset["height"]) == (1920, 960)
    assert (
        client.post(
            "/api/admin/upload/image", files={"file": ("evil.svg", b"<svg/>", "image/svg+xml")}
        ).status_code
        == 422
    )


def test_target_controls_and_commands(setup):
    app, client, _ = setup
    group, other = app.state.db.all("group")[:2]
    d1, h1 = pair_device(client, group)
    d2, h2 = pair_device(client, other)
    result = client.post(
        "/api/admin/control", json={"target": {"kind": "group", "id": group["id"]}, "mode": "messages"}
    )
    assert result.json()["changed"] == [d1["id"]]
    assert sync(client, h1)["manifest"]["manual"]["mode"] == "messages"
    assert sync(client, h2)["manifest"]["manual"] is None
    command = client.post(f"/api/admin/devices/{d1['id']}/commands/restart").json()["id"]
    assert sync(client, h2, ack=[command])["commands"] == []
    assert sync(client, h1)["commands"][0]["id"] == command
    assert sync(client, h1, ack=[command])["commands"] == []
    assert client.delete("/api/admin/devices/" + d1["id"]).status_code == 200
    assert client.post("/api/device/sync", json={}, headers=h1).status_code == 401


@pytest.mark.parametrize("path", ["../secret", "/etc/passwd", "C:/Windows", "x/../../bad", "x\\..\\bad"])
def test_paths_cannot_escape_nas(tmp_path, path):
    with pytest.raises(ValueError):
        within(tmp_path, path)


def test_invalid_settings_rejected(setup):
    app, client, _ = setup
    group = app.state.db.all("group")[0]
    response = client.post(
        "/api/admin/devices", json={"name": "Pi", "group_id": group["id"], "settings": {"interval": 0}}
    )
    assert response.status_code == 422
    assert (
        client.put(
            "/api/admin/operating-hours", json={"enabled": True, "windows": [{"days": [9]}]}
        ).status_code
        == 422
    )
    assert (
        client.put(
            "/api/admin/notices/new", json={"title": "Test", "ends_at": "2026-01-01T12:00:00"}
        ).status_code
        == 422
    )
    settings = Settings().model_dump()
    settings["operating_hours_override"] = {
        "enabled": True,
        "windows": [{"days": [0], "start": "07:00", "end": "18:00"}],
    }
    device, _ = pair_device(client, group, settings=settings)
    preview = client.get("/api/admin/preview/" + device["id"] + "?at=2026-09-14T22:00:00Z").json()
    assert preview["decision"]["mode"] == "black"


def test_new_public_nas_plan_cannot_expose_previous_internal_snapshot(setup):
    app, client, config = setup
    group = app.state.db.all("group")[0]
    folder = config.nas_root / group["folder"]
    (folder / "Personal.jpg").write_bytes(image_bytes("red"))
    client.put(
        "/api/admin/groups/" + group["id"],
        json={"name": group["name"], "folder": group["folder"], "plan_path": "Personal.jpg"},
    )
    app.state.media.scan()
    _, parent = pair_device(client, group)
    old_plan = app.state.db.get("snapshot", group["id"])["plan"][0]
    (folder / "Eltern.jpg").write_bytes(image_bytes("blue"))
    (folder / "Personal.jpg").unlink()
    client.put(
        "/api/admin/groups/" + group["id"],
        json={
            "name": group["name"],
            "folder": group["folder"],
            "plan_path": "Eltern.jpg",
            "plan_public": True,
        },
    )
    before_scan = sync(client, parent)["manifest"]
    assert before_scan["plan"] == []
    assert old_plan not in before_scan["assets"]
    app.state.media.scan()
    after_scan = sync(client, parent)["manifest"]
    assert len(after_scan["plan"]) == 1
    assert old_plan not in after_scan["assets"]


def test_replacing_public_upload_resets_permission_atomically(setup):
    app, client, _ = setup
    group = app.state.db.all("group")[0]
    _, parent = pair_device(client, group)
    first = client.post(
        "/api/admin/upload/plan", files={"file": ("Eltern.jpg", image_bytes("blue"), "image/jpeg")}
    ).json()
    second = client.post(
        "/api/admin/upload/plan", files={"file": ("Personal.jpg", image_bytes("red"), "image/jpeg")}
    ).json()
    client.put(f"/api/admin/groups/{group['id']}/plan/{first['id']}", json={"plan_public": True})
    assert sync(client, parent)["manifest"]["plan"] == first["assets"]
    client.put(f"/api/admin/groups/{group['id']}/plan/{second['id']}")
    assert sync(client, parent)["manifest"]["plan"] == []
