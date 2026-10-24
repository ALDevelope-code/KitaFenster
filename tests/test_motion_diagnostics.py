from types import SimpleNamespace

import pytest
from conftest import pair_device, sync
from test_motion import Sensor, settings
from test_player import LocalAPI

from player.client import SyncWorker
from player.motion import MotionGate
from server.motion_diagnostics import MotionDiagnostics


@pytest.mark.parametrize("sample_at", [0.0, 52.00000000000002])
def test_live_roundtrip_is_per_device_ephemeral_and_does_not_sync_media(
    setup, tmp_path, monkeypatch, sample_at
):
    app, client, _ = setup
    first, auth = pair_device(client, app.state.db.all("group")[0], settings={"motion": settings()})
    second, other_auth = pair_device(client, app.state.db.all("group")[0])
    path = f"/api/admin/devices/{first['id']}/motion"
    now = [0]
    app.state.motion_diagnostics.clock = lambda: now[0]
    assert client.get(path).json()["active"] is False
    assert client.post(path).json()["active"] is True
    assert sync(client, other_auth)["motion_diagnostics"] is False
    worker = SyncWorker({"cache_dir": str(tmp_path / "cache")}, api=LocalAPI(client, auth))
    worker.sync_once()
    assert worker.diagnostics_active
    state_before = worker.state_path.read_bytes()
    device_before = app.state.db.get("device", first["id"])
    sensor = Sensor()
    sensor.high = True
    gate = MotionGate(lambda: sensor)
    gate.update(settings(), 0)
    reading = gate.update(settings(), 61)
    worker.report("photos", reading.reason, "", {**reading.diagnostics, "display": "on", "display_error": ""})
    worker.diagnostics_once()
    result = client.get(path).json()
    assert result["sample"]["phase"] == "high"
    assert result["sample"]["signal"] is True
    assert result["sample"]["remaining_seconds"] == 60
    assert result["settings"] == settings()
    assert client.get(f"/api/admin/devices/{second['id']}/motion").json()["sample"] is None
    assert worker.state_path.read_bytes() == state_before
    assert app.state.db.get("device", first["id"]) == device_before
    now[0] = 8
    assert client.get(path).json()["age_seconds"] >= 8
    # Even a fresh network packet must expose a stalled render loop's old sample.
    # Crossing a float exponent boundary can produce 12.000000000000007 seconds.
    # Replace only this module's clock so the HTTP test client's event loop keeps real time.
    worker.motion_sample_at = sample_at
    monkeypatch.setattr("player.client.time", SimpleNamespace(monotonic=lambda: sample_at + 12))
    worker.diagnostics_once()
    assert client.get(path).json()["age_seconds"] == pytest.approx(12, rel=0, abs=1e-6)
    now[0] = 31
    assert client.get(path).json()["sample"] is None
    worker.diagnostics_once()
    assert not worker.diagnostics_active
    assert client.post(path).json()["sample"] is None


def test_diagnostic_access_requires_admin_csrf_or_paired_device(setup):
    app, client, _ = setup
    device, auth = pair_device(client, app.state.db.all("group")[0])
    path = f"/api/admin/devices/{device['id']}/motion"
    csrf = client.headers.pop("X-CSRF-Token")
    assert client.post(path).status_code == 403
    client.headers["X-CSRF-Token"] = csrf
    assert client.post(path).status_code == 200
    assert client.post("/api/admin/devices/unknown/motion").status_code == 404
    assert client.post("/api/device/motion", json={}).status_code == 401
    # A device cannot choose another device's diagnostics slot.
    assert client.post("/api/device/motion", json={"device_id": "other"}, headers=auth).status_code == 422
    client.cookies.clear()
    assert client.get(path).status_code == 401
    assert client.post(path, headers=auth).status_code == 401
    assert client.post("/api/device/motion", json={}, headers=auth).status_code == 200


def test_leases_renew_and_expire_without_retaining_signal_history():
    now = [0]
    diagnostics = MotionDiagnostics(clock=lambda: now[0])
    diagnostics.start("one")
    diagnostics.start("two")
    diagnostics.report("one", {"sample_age_seconds": 0})
    now[0] = 20
    diagnostics.start("one")
    now[0] = 31
    assert diagnostics.snapshot("one")["sample"] is not None
    assert not diagnostics.snapshot("two")["active"]
    now[0] = 50
    assert not diagnostics.report("one", {"sample_age_seconds": 0})
    assert diagnostics.sessions == {}


@pytest.mark.parametrize("diagnostic_failure", [False, True])
def test_live_polling_preserves_regular_sync_interval(tmp_path, monkeypatch, diagnostic_failure):
    worker = SyncWorker({"cache_dir": str(tmp_path)}, api=SimpleNamespace())
    now, syncs, reports = [0.0], [], []
    monkeypatch.setattr("player.client.time.monotonic", lambda: now[0])
    worker.stop = SimpleNamespace(
        is_set=lambda: now[0] >= 35, wait=lambda delay: now.__setitem__(0, now[0] + delay)
    )

    def regular_sync():
        syncs.append(now[0])
        worker.diagnostics_active = True

    def diagnostic():
        reports.append(now[0])
        if diagnostic_failure:
            raise OSError("NAS unreachable")

    monkeypatch.setattr(worker, "sync_once", regular_sync)
    monkeypatch.setattr(worker, "diagnostics_once", diagnostic)
    worker.run()
    assert syncs == [0, 15, 30]
    assert reports == list(range(0, 35, 5 if diagnostic_failure else 1))
    assert worker.player_error == ""


def test_old_server_response_keeps_diagnostics_off(setup, tmp_path):
    app, client, _ = setup
    _, auth = pair_device(client, app.state.db.all("group")[0])
    response = sync(client, auth)
    response.pop("motion_diagnostics")
    worker = SyncWorker(
        {"cache_dir": str(tmp_path)}, api=SimpleNamespace(sync=lambda _: response, asset=lambda *_: None)
    )
    worker.sync_once()
    assert not worker.diagnostics_active
