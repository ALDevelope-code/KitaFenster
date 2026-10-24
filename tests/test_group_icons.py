import io
import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from test_branding import png_logo

from server.app import create_app
from server.branding import MAX_LOGO_BYTES
from server.config import Config
from server.db import Database
from server.manage import backup, restore


def edit(client, group, *, action="keep", image=None, **changes):
    body = {key: group.get(key, "") for key in ("name", "folder", "plan_path")}
    body["plan_public"] = group.get("plan_public", False)
    body.update(changes)
    return client.post(
        f"/api/admin/groups/{group['id']}/edit",
        data={"data": json.dumps(body), "icon_action": action},
        files={"file": ("../../private.png", image, "application/octet-stream")}
        if image is not None
        else None,
    )


def test_group_icon_lifecycle_keeps_group_assignments_and_other_groups(setup):
    app, client, _ = setup
    db = app.state.db
    group, other = db.all("group")[:2]
    db.mutate("group", group["id"], {"plan_id": "existing-document"})
    response = edit(client, group, action="replace", image=png_logo(), name="Piraten")
    assert response.status_code == 200, response.text
    actual = response.json()
    assert actual["plan_id"] == "existing-document"
    image_response = client.get(actual["icon_url"])
    assert image_response.headers["content-type"] == "image/png"
    assert image_response.headers["cache-control"] == "no-store"
    normalized = Image.open(io.BytesIO(image_response.content))
    assert normalized.size == (256, 128)
    assert normalized.getpixel((10, 10))[3] == 100
    assert "private-note" not in normalized.info
    state = client.get("/api/admin/state").json()
    visible = next(g for g in state["groups"] if g["id"] == group["id"])
    assert visible == actual
    assert "logo" not in visible
    assert not next(g for g in state["groups"] if g["id"] == other["id"])["icon_url"]
    updated = edit(client, actual, name="Seeräuber").json()
    assert updated["icon_url"] == actual["icon_url"]
    legacy = client.put(
        f"/api/admin/groups/{group['id']}", json={"name": "Neuer Name", "folder": group["folder"]}
    ).json()
    assert legacy["icon_url"] == actual["icon_url"]
    replaced = edit(client, legacy, action="replace", image=png_logo((400, 400))).json()
    assert replaced["icon_url"] != actual["icon_url"]
    removed = edit(client, replaced, action="remove").json()
    assert removed["icon_url"] is None
    assert removed["plan_id"] == "existing-document"
    assert db.get("group_icon", group["id"]) is None
    assert client.get(actual["icon_url"]).status_code == 404
    assert db.get("group", other["id"]) == other


def test_create_group_with_icon_and_restart_backup_restore(setup, tmp_path):
    app, client, config = setup
    response = edit(
        client, {"id": "new", "name": "Sterne", "folder": "Sterne"}, action="replace", image=png_logo()
    )
    assert response.status_code == 200, response.text
    group = response.json()
    original = client.get(group["icon_url"]).content
    restored_config = Config(tmp_path / "restored", config.nas_root, background_scan=False)
    restore(restored_config, backup(config, tmp_path / "backup.zip"))
    for target in (config, restored_config):
        with TestClient(create_app(target)) as reopened:
            assert (
                reopened.post(
                    "/api/login", json={"username": "admin", "password": "Nur-fuer-Tests-123!"}
                ).status_code
                == 200
            )
            assert reopened.get(group["icon_url"]).content == original


def test_invalid_icon_or_group_does_not_partially_save(setup):
    app, client, _ = setup
    group = app.state.db.all("group")[0]
    assert edit(client, group, action="replace", image=png_logo()).status_code == 200
    before = app.state.db.get("group", group["id"])
    icon = app.state.db.get("group_icon", group["id"])
    for image in (b"bad", b"<svg></svg>", png_logo((2001, 2000))):
        assert edit(client, group, action="replace", image=image, name="Do not save").status_code == 422
    assert edit(client, group, action="replace", image=b"x" * (MAX_LOGO_BYTES + 1)).status_code == 413
    assert edit(client, group, action="replace").status_code == 422
    assert edit(client, group, image=png_logo()).status_code == 422
    assert edit(client, group, action="remove", folder="../outside").status_code == 422
    assert edit(client, group, action="remove", name="").status_code == 422
    assert app.state.db.get("group", group["id"]) == before
    assert app.state.db.get("group_icon", group["id"]) == icon
    count = len(app.state.db.all("group"))
    assert edit(client, {**group, "id": "new"}, action="replace", image=b"bad").status_code == 422
    assert len(app.state.db.all("group")) == count


def test_icon_write_and_group_edit_roll_back_together(setup, monkeypatch):
    app, client, _ = setup
    group = app.state.db.all("group")[0]
    original = Database.write

    def fail_group(connection, kind, value):
        if kind == "group":
            raise RuntimeError("simulated failure")
        original(connection, kind, value)

    monkeypatch.setattr(Database, "write", staticmethod(fail_group))
    with pytest.raises(RuntimeError, match="simulated failure"):
        edit(client, group, action="replace", image=png_logo(), name="Do not save")
    assert app.state.db.get("group", group["id"]) == group
    assert app.state.db.get("group_icon", group["id"]) is None


def test_group_icon_access_and_request_limits(setup):
    app, client, _ = setup
    group = app.state.db.all("group")[0]
    assert edit(client, {**group, "id": "missing"}, action="replace", image=png_logo()).status_code == 404
    response = edit(client, group, action="replace", image=png_logo())
    url = response.json()["icon_url"]
    with TestClient(app) as visitor:
        assert visitor.get(url).status_code == 401
        assert edit(visitor, group, action="remove").status_code == 401
    client.headers.pop("X-CSRF-Token")
    assert edit(client, group, action="remove").status_code == 403
    response = client.post(f"/api/admin/groups/{group['id']}/edit", content=b"x" * (MAX_LOGO_BYTES + 65537))
    assert response.status_code == 413
