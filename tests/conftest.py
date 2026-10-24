import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from server.app import create_app
from server.config import Config
from server.manage import set_admin


@pytest.fixture
def setup(tmp_path):
    config = Config(tmp_path / "data", tmp_path / "nas", background_scan=False)
    app = create_app(config)
    config.nas_root.mkdir()
    (config.nas_root / ".bilderrahmen-source").touch()
    for group in app.state.db.all("group"):
        (config.nas_root / group["folder"]).mkdir()
    set_admin(app.state.db, "admin", "Nur-fuer-Tests-123!")
    with TestClient(app) as client:
        response = client.post("/api/login", json={"username": "admin", "password": "Nur-fuer-Tests-123!"})
        client.headers["X-CSRF-Token"] = response.json()["csrf"]
        yield app, client, config


def image_bytes(color="red", size=(600, 300)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, "JPEG")
    return buffer.getvalue()


def pair_device(client, group, internal=False, settings=None):
    body = {"name": "Vorraum " + group["name"], "group_id": group["id"], "allow_internal": internal}
    if settings:
        body["settings"] = settings
    response = client.post("/api/admin/devices", json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    paired = client.post("/api/device/pair", json={"code": result["code"]})
    assert paired.status_code == 200
    headers = {"Authorization": "Bearer " + paired.json()["token"]}
    return result["device"], headers


def sync(client, headers, **kwargs):
    response = client.post("/api/device/sync", json=kwargs, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()
