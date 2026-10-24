import pytest
from conftest import pair_device, sync
from test_player import LocalAPI

from player.client import SyncWorker


def test_motion_settings_are_per_device_persist_and_survive_offline_restart(setup, tmp_path):
    app, client, _ = setup
    group = app.state.db.all("group")[0]
    first, headers = pair_device(
        client, group, settings={"motion": {"enabled": True, "idle_minutes": 7, "power_mode": "black"}}
    )
    second, other_headers = pair_device(client, group)
    worker = SyncWorker({"cache_dir": str(tmp_path)}, api=LocalAPI(client, headers))
    worker.sync_once()
    assert worker.snapshot()["settings"]["motion"]["idle_minutes"] == 7
    offline = SyncWorker({"cache_dir": str(tmp_path)}, api=LocalAPI(client, headers))
    assert offline.snapshot()["settings"]["motion"]["enabled"]
    assert not sync(client, other_headers)["manifest"]["settings"]["motion"]["enabled"]
    worker.report("sleep", "Keine Bewegung erkannt · Schwarzbild", "Sensor-Testhinweis")
    worker.sync_once()
    saved = app.state.db.get("device", first["id"])
    assert saved["reported"]["mode"] == "sleep"
    assert saved["reported"]["error"] == "Sensor-Testhinweis"
    assert app.state.db.get("device", second["id"])["settings"]["motion"]["enabled"] is False
    result = client.put(
        "/api/admin/devices/" + first["id"],
        json={"name": first["name"], "group_id": group["id"], "settings": {"motion": {"enabled": False}}},
    )
    assert result.status_code == 200
    worker.report("photos", "Standardanzeige")
    worker.sync_once()
    assert not worker.snapshot()["settings"]["motion"]["enabled"]
    assert not app.state.db.get("device", first["id"])["reported"]["error"]


@pytest.mark.parametrize("motion", [{"idle_minutes": 0}, {"idle_minutes": 241}, {"power_mode": "shell"}])
def test_invalid_motion_settings_are_rejected(setup, motion):
    app, client, _ = setup
    group = app.state.db.all("group")[0]
    result = client.post(
        "/api/admin/devices",
        json={"name": "Raum", "group_id": group["id"], "settings": {"motion": motion}},
    )
    assert result.status_code == 422
