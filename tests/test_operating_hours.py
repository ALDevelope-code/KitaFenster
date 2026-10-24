import pytest
from conftest import pair_device, sync
from test_player import LocalAPI
from test_schedule import at, base

from player.client import SyncWorker
from shared.schedule import resolve


def hours(start="07:00", end="18:00", days=None, enabled=True, timezone="Europe/Berlin"):
    return {
        "enabled": enabled,
        "timezone": timezone,
        "windows": [{"days": days or [0, 1, 2, 3, 4], "start": start, "end": end}],
    }


def test_operating_times_gate_both_areas_manual_and_content_windows():
    m = base()
    m["operating_hours"] = hours()
    m["settings"]["split"]["enabled"] = True
    m["settings"]["content_windows"] = [
        {"days": [0], "start": "00:00", "end": "00:00", "mode": "plan", "area": area}
        for area in ("main", "secondary")
    ]
    # Windows running all day do not extend central operating hours.
    assert resolve(m, at("2026-09-14T04:59:59"))["mode"] == "black"
    opened = resolve(m, at("2026-09-14T05:00:00"))
    assert opened["mode"] == opened["secondary"]["mode"] == "plan"
    m["manual"] = {"mode": "messages"}
    m["manual_secondary"] = {"mode": "photos"}
    assert resolve(m, at("2026-09-14T16:00:00"))["mode"] == "black"
    m["settings"]["content_windows_enabled"] = False
    assert resolve(m, at("2026-09-14T16:00:00"))["mode"] == "black"
    m["notices"] = [{"id": "urgent", "urgent": True}]
    result = resolve(m, at("2026-09-14T16:00:00"))
    assert result["reason"] == "Sofortmeldung" and "secondary" not in result


def test_empty_hours_explicitly_close_and_disabled_hours_allow_all_day():
    m = base()
    m["operating_hours"] = {"enabled": True, "timezone": "Europe/Berlin", "windows": []}
    assert resolve(m, at("2026-09-14T10:00:00"))["mode"] == "black"
    m["operating_hours"]["enabled"] = False
    assert resolve(m, at("2026-09-14T10:00:00"))["mode"] == "photos"


def test_overnight_union_dst_and_separate_content_timezone():
    m = base()
    m["operating_hours"] = hours("22:00", "02:00", days=[0], timezone="UTC")
    m["settings"]["timezone"] = "Europe/Berlin"
    m["settings"]["content_windows"] = [{"days": [1], "start": "00:00", "end": "01:00", "mode": "plan"}]
    assert resolve(m, at("2026-09-14T22:00:00"))["mode"] == "plan"
    assert resolve(m, at("2026-09-15T01:59:59"))["mode"] == "photos"
    assert resolve(m, at("2026-09-15T02:00:00"))["mode"] == "black"
    m["operating_hours"]["windows"].append({"days": [1], "start": "01:00", "end": "03:00"})
    assert resolve(m, at("2026-09-15T02:00:00"))["mode"] == "photos"
    m["operating_hours"] = hours("02:00", "03:00", days=[6])
    assert resolve(m, at("2026-10-25T00:30:00"))["mode"] == "photos"
    assert resolve(m, at("2026-10-25T01:30:00"))["mode"] == "photos"
    assert resolve(m, at("2026-10-25T02:00:00"))["mode"] == "black"


def test_global_default_override_reset_and_future_devices(setup, tmp_path):
    app, client, _ = setup
    group = app.state.db.all("group")[0]
    first, auth = pair_device(client, group)
    override, other_auth = pair_device(
        client, group, settings={"operating_hours_override": hours(enabled=False)}
    )
    assert client.put("/api/admin/operating-hours", json=hours()).status_code == 200
    global_manifest = sync(client, auth)["manifest"]
    assert global_manifest["operating_hours"] == hours()
    assert not sync(client, other_auth)["manifest"]["operating_hours"]["enabled"]
    future, future_auth = pair_device(client, group)
    assert sync(client, future_auth)["manifest"]["operating_hours"] == hours()
    # Changing central settings cannot overwrite an explicit override.
    closed = {"enabled": True, "timezone": "Europe/Berlin", "windows": []}
    client.put("/api/admin/operating-hours", json=closed)
    assert not sync(client, other_auth)["manifest"]["operating_hours"]["enabled"]
    response = client.put(
        f"/api/admin/devices/{override['id']}",
        json={
            "name": override["name"],
            "group_id": group["id"],
            "settings": {"operating_hours_override": None},
        },
    )
    assert response.status_code == 200
    assert sync(client, other_auth)["manifest"]["operating_hours"] == closed
    # The server preview and the offline player use the same effective hours.
    transport = LocalAPI(client, auth)
    cfg = {"cache_dir": str(tmp_path / "player")}
    worker = SyncWorker(cfg, api=transport)
    worker.sync_once()
    transport.offline = True
    restarted = SyncWorker(cfg, api=transport)
    with pytest.raises(OSError):
        restarted.sync_once()
    preview = client.get(f"/api/admin/preview/{first['id']}").json()
    assert resolve(restarted.snapshot()) == preview["decision"]
    assert preview["decision"]["mode"] == "black"
    client.put("/api/admin/operating-hours", json=hours(enabled=False))
    assert resolve(restarted.snapshot())["mode"] == "black"
    transport.offline = False
    restarted.sync_once()
    assert resolve(restarted.snapshot())["mode"] == "photos"
    state = client.get("/api/admin/state").json()
    assert "operating_hours" in state and "schedules" not in state


def test_operating_configuration_validation_and_authorization(setup):
    _, client, _ = setup
    url = "/api/admin/operating-hours"
    for body in [
        hours(days=[9]),
        hours(start="25:00"),
        hours(timezone="invalid/zone"),
        {**hours(), "mode": "photos"},
    ]:
        assert client.put(url, json=body).status_code == 422
    assert client.put("/api/admin/schedules/new", json={"name": "Removed"}).status_code == 405
    del client.headers["X-CSRF-Token"]
    assert client.put(url, json=hours()).status_code == 403
    client.cookies.clear()
    assert client.put(url, json=hours()).status_code == 401
