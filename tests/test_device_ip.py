from fastapi.testclient import TestClient

from tests.conftest import pair_device, sync


def test_admin_sees_connection_ip_after_device_sync(setup):
    app, admin, _ = setup
    device, auth = pair_device(admin, app.state.db.all("group")[0])

    with TestClient(app, client=("192.168.10.42", 43210)) as player:
        response = player.post(
            "/api/device/sync",
            json={"mode": "photos"},
            headers={**auth, "X-Forwarded-For": "203.0.113.8"},
        )
        assert response.status_code == 200

    shown = next(d for d in admin.get("/api/admin/state").json()["devices"] if d["id"] == device["id"])
    assert shown["last_ip"] == "192.168.10.42"

    sync(admin, auth, mode="photos")
    assert app.state.db.get("device", device["id"])["last_ip"] == "192.168.10.42"
