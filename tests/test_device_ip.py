from fastapi.testclient import TestClient
from test_player import LocalAPI

from player.client import SyncWorker, local_ip_for_server
from tests.conftest import pair_device


def test_player_reports_own_ip_instead_of_docker_gateway(setup, tmp_path, monkeypatch):
    app, admin, _ = setup
    device, auth = pair_device(admin, app.state.db.all("group")[0])
    monkeypatch.setattr("player.client.local_ip_for_server", lambda _: "192.168.10.42")

    with TestClient(app, client=("172.21.0.1", 43210)) as connection:
        worker = SyncWorker(
            {"cache_dir": str(tmp_path), "server_url": "http://nas:8088"},
            api=LocalAPI(connection, auth),
        )
        worker.sync_once()
        assert app.state.db.get("device", device["id"])["reported"]["local_ip"] is None

        worker.sync_once()

    shown = next(d for d in admin.get("/api/admin/state").json()["devices"] if d["id"] == device["id"])
    assert shown["reported"]["local_ip"] == "192.168.10.42"
    assert "last_ip" not in shown


def test_player_ip_is_checked_before_storage(setup):
    app, admin, _ = setup
    device, auth = pair_device(admin, app.state.db.all("group")[0])
    response = admin.post("/api/device/sync", json={"local_ip": "not-an-ip"}, headers=auth)
    assert response.status_code == 422
    assert app.state.db.get("device", device["id"])["reported"] == {}


def test_local_ip_uses_route_toward_server():
    assert local_ip_for_server("http://127.0.0.1:8088") == "127.0.0.1"
