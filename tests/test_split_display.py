import copy
import os
from datetime import datetime, timezone

import pytest
from conftest import image_bytes, pair_device, sync

from player.cache import Cache
from player.client import SyncWorker
from server.models import OperatingHours, Settings
from shared.layout import region_rects
from shared.schedule import document_references, resolve, slides

NOW = datetime(2026, 9, 14, 10, tzinfo=timezone.utc)


def manifest():
    settings = Settings(
        split={"enabled": True, "secondary": {"default_mode": "messages", "interval": 20}}
    ).model_dump()
    return {
        "settings": settings,
        "photos": ["photo"],
        "plan": ["plan"],
        "group_name": "Test",
        "notices": [{"id": "n", "title": "Hallo", "text": "Test", "theme": "ocean"}],
        "operating_hours": OperatingHours().model_dump(),
        "manual": None,
    }


def hour(area, mode, start="07:00", end="18:00"):
    return {"area": area, "mode": mode, "days": [0], "start": start, "end": end}


def test_content_windows_are_independent_and_never_close_the_screen():
    m = manifest()
    m["settings"]["content_windows"] = [
        hour("secondary", "plan"),
        hour("main", "photos"),
        hour("secondary", "photos"),
    ]
    result = resolve(m, NOW)
    assert result["mode"] == "photos" and result["secondary"]["mode"] == "plan"
    m["settings"]["content_windows"][1]["end"] = "08:00"
    assert resolve(m, NOW)["mode"] == "photos"
    m["settings"]["content_windows"] = [hour("secondary", "plan", "07:00", "08:00")]
    assert resolve(m, NOW)["mode"] == "photos"
    assert resolve(m, NOW)["secondary"]["mode"] == "messages"
    m["settings"]["content_windows_enabled"] = False
    m["settings"]["content_windows"] = [hour("secondary", "plan")]
    assert resolve(m, NOW)["secondary"]["mode"] == "messages"


def test_manual_and_content_windows_target_each_area_and_urgent_is_fullscreen():
    m = manifest()
    m["settings"]["content_windows"] = [hour("secondary", "plan")]
    assert resolve(m, NOW)["mode"] == "photos"
    assert resolve(m, NOW)["secondary"]["mode"] == "plan"
    m["manual_secondary"] = {"mode": "photos", "until": "2026-09-14T11:00:00+00:00"}
    assert resolve(m, NOW)["secondary"]["mode"] == "photos"
    m["manual_secondary"]["until"] = NOW.isoformat()
    assert resolve(m, NOW)["secondary"]["mode"] == "plan"
    m["notices"][0]["urgent"] = True
    m["settings"]["content_windows"] = [hour("main", "photos", "07:00", "08:00")]
    urgent = resolve(m, NOW)
    assert urgent["reason"] == "Sofortmeldung" and "secondary" not in urgent
    assert len(slides(m, urgent)) == 1


@pytest.mark.parametrize("size", [(1920, 1080), (1080, 1920)])
@pytest.mark.parametrize("percent", [33, 40, 50])
@pytest.mark.parametrize("position", ["first", "second"])
def test_layout_covers_screen_without_gaps_or_overlap(size, percent, position):
    split = {"enabled": True, "secondary_percent": percent, "main_position": position}
    rects = region_rects(size, split, True)
    a, b = rects.values()
    assert a[2] * a[3] + b[2] * b[3] == size[0] * size[1]
    axis = 1 if size[1] > size[0] else 0
    assert b[axis + 2] == round(size[axis] * percent / 100)
    assert (a[axis] == 0) == (position == "first")
    assert a[axis] + a[axis + 2] == b[axis] or b[axis] + b[axis + 2] == a[axis]
    assert region_rects(size, split, False) == {"main": (0, 0, *size)}


def test_explicit_direction_and_legacy_settings():
    assert (
        region_rects((1080, 1920), {"enabled": True, "direction": "horizontal"}, True)["secondary"][0] == 724
    )
    assert region_rects((1920, 1080), {"enabled": True, "direction": "vertical"}, True)["secondary"][1] == 724
    m = manifest()
    del m["settings"]["split"]
    assert "secondary" not in resolve(m, NOW)
    m["settings"]["content_windows"] = [{"mode": "plan", "days": [0], "start": "07:00", "end": "18:00"}]
    assert resolve(m, NOW)["mode"] == "plan"


def test_secondary_mixed_playlist_and_document_references():
    m = manifest()
    secondary = m["settings"]["split"]["secondary"]
    secondary.update(
        default_mode="mixed",
        document_id="paused",
        playlist=[{"mode": "plan", "seconds": 7, "document_id": "menu"}, {"mode": "photos", "seconds": 4}],
    )
    m["documents"] = {"menu": {"assets": ["page"]}}
    result = slides(m, resolve(m, NOW)["secondary"])
    assert [(s["asset"], s["seconds"]) for s in result] == [("page", 7), ("photo", 4)]
    assert document_references(m["settings"]) == {"paused", "menu"}


def test_secondary_permissions_preview_controls_and_document_deletion(setup):
    app, client, _ = setup
    group = app.state.db.all("group")[0]
    doc = client.post("/api/admin/upload/plan", files={"file": ("Personal.jpg", image_bytes())}).json()
    settings = Settings(
        split={
            "enabled": True,
            "secondary_percent": 40,
            "main_position": "second",
            "secondary": {"default_mode": "plan", "document_id": doc["id"]},
        }
    ).model_dump()
    body = {"name": "Test", "group_id": group["id"], "settings": settings}
    assert client.post("/api/admin/devices", json=body).status_code == 422
    device, auth = pair_device(client, group, internal=True, settings=settings)
    paired = sync(client, auth)["manifest"]
    assert doc["id"] in paired["documents"]
    assert paired["settings"]["split"]["secondary_percent"] == 40
    assert paired["settings"]["split"]["main_position"] == "second"
    preview = client.get(f"/api/admin/preview/{device['id']}").json()
    assert preview["secondary_slides"][0]["asset"] == doc["assets"][0]
    client.post(
        "/api/admin/control",
        json={"target": {"kind": "device", "id": device["id"]}, "area": "secondary", "mode": "messages"},
    )
    current = app.state.db.get("device", device["id"])
    assert current.get("manual") is None and current["manual_secondary"]["mode"] == "messages"
    # A later permissions change removes the document from both download paths and preview.
    app.state.db.mutate("device", device["id"], {"allow_internal": False, "manual_secondary": None})
    denied = sync(client, auth)["manifest"]
    assert doc["id"] not in denied["documents"]
    assert client.get("/api/device/assets/" + doc["assets"][0], headers=auth).status_code == 404
    assert client.get(f"/api/admin/preview/{device['id']}").json()["secondary_slides"] == []
    usage = client.get(f"/api/admin/documents/{doc['id']}/usage").json()
    assert any(r["slot"] == "secondary" for r in usage["references"])
    assert client.delete(f"/api/admin/documents/{doc['id']}").status_code == 409
    assert (
        client.delete(
            f"/api/admin/documents/{doc['id']}?unlink=true&revision={usage['revision']}"
        ).status_code
        == 200
    )
    assert app.state.db.get("device", device["id"])["settings"]["split"]["secondary"]["document_id"] is None


def test_player_clocks_transitions_and_fullscreen_fallback(tmp_path):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame

    from player.presentation import Presentation

    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((600, 360))
    try:
        cache = Cache(tmp_path)
        ids = ["a" * 64, "b" * 64]
        for id, color in zip(ids, ["red", "blue"]):
            cache.path(id).write_bytes(image_bytes(color))
        m = manifest()
        m["photos"] = ids
        m["settings"]["interval"] = 3
        player = Presentation()
        first, _ = player.frame(m, resolve(m, NOW), (600, 360), 0, cache)
        assert first.get_at((100, 100)).r > 200
        secondary = player.regions["secondary"]
        surface = secondary.current
        player.frame(m, resolve(m, NOW), (600, 360), 3, cache)
        assert player.regions["main"].item["asset"] == ids[1]
        assert secondary.current is surface and secondary.next_slide == 20
        changed = copy.deepcopy(m)
        changed["notices"][0]["text"] = "Neue Nachricht"
        player.frame(changed, resolve(changed, NOW), (600, 360), 4, cache)
        assert player.regions["main"].next_slide == 6
        changed["notices"] = []
        full, _ = player.frame(changed, resolve(changed, NOW), (600, 360), 5, cache)
        assert set(player.regions) == {"main"}
        assert player.regions["main"].size == (600, 360) and player.regions["main"].next_slide == 6
        assert full.get_at((500, 100)).b > 200
        m["settings"]["rotation"] = 90
        rotated, _ = player.frame(m, resolve(m, NOW), (600, 360), 7, cache)
        assert rotated.get_size() == (600, 360)
        assert player.regions["main"].size == (360, 402)
        m["notices"][0]["urgent"] = True
        player.frame(m, resolve(m, NOW), (600, 360), 8, cache)
        assert set(player.regions) == {"main"} and player.regions["main"].size == (360, 600)
    finally:
        pygame.quit()


def test_secondary_document_survives_offline_restart_and_revocation_clears_cache(setup, tmp_path):
    from test_player import LocalAPI

    app, client, _ = setup
    group = app.state.db.all("group")[0]
    document = client.post("/api/admin/upload/plan", files={"file": ("Personal.jpg", image_bytes())}).json()
    settings = Settings(
        split={
            "enabled": True,
            "secondary": {
                "default_mode": "plan",
                "document_id": document["id"],
            },
        }
    ).model_dump()
    device, auth = pair_device(client, group, internal=True, settings=settings)
    transport = LocalAPI(client, auth)
    config = {"cache_dir": str(tmp_path / "player")}
    worker = SyncWorker(config, api=transport)
    worker.sync_once()
    transport.offline = True
    restarted = SyncWorker(config, api=transport)
    offline = restarted.snapshot()
    items = slides(offline, resolve(offline, NOW)["secondary"])
    assert items[0]["asset"] == document["assets"][0]
    assert restarted.cache.path(items[0]["asset"]).is_file()
    with pytest.raises(OSError):
        restarted.sync_once()
    assert restarted.snapshot() == offline
    transport.offline = False
    app.state.db.mutate("device", device["id"], {"allow_internal": False})
    restarted.sync_once()
    assert slides(restarted.snapshot(), resolve(restarted.snapshot(), NOW)["secondary"]) == []
    assert not restarted.cache.path(items[0]["asset"]).exists()


def test_deleting_document_clears_secondary_playlist_windows_and_manual_mode(setup):
    app, client, _ = setup
    group = app.state.db.all("group")[0]
    doc = client.post("/api/admin/upload/plan", files={"file": ("Plan.jpg", image_bytes())}).json()
    settings = Settings(
        split={
            "enabled": True,
            "secondary": {
                "default_mode": "plan",
                "document_id": doc["id"],
                "playlist": [{"mode": "plan", "seconds": 7, "document_id": doc["id"]}],
            },
        },
        content_windows=[{**hour("secondary", "plan"), "document_id": doc["id"]}],
    ).model_dump()
    device, _ = pair_device(client, group, internal=True, settings=settings)
    app.state.db.mutate("device", device["id"], {"manual_secondary": {"mode": "plan"}})
    usage = client.get(f"/api/admin/documents/{doc['id']}/usage").json()
    assert {r["slot"] for r in usage["references"]} == {"secondary", "secondary-playlist:0", "hour:0"}
    response = client.delete(f"/api/admin/documents/{doc['id']}?unlink=true&revision={usage['revision']}")
    assert response.status_code == 200
    saved = app.state.db.get("device", device["id"])
    assert saved["manual_secondary"] is None
    assert not document_references(saved["settings"])
    secondary = saved["settings"]["split"]["secondary"]
    assert secondary["default_mode"] == "photos" and secondary["playlist"][0]["mode"] == "photos"
    assert saved["settings"]["content_windows"][0]["mode"] == "photos"
