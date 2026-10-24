import pytest
from conftest import image_bytes, pair_device
from test_display_windows import upload, window

from server.db import Database
from server.models import Settings
from shared.schedule import document_references


def assign(client, group, doc, public=True):
    response = client.put(f"/api/admin/groups/{group['id']}/plan/{doc['id']}", json={"plan_public": public})
    assert response.status_code == 200, response.text


def usage(client, doc):
    response = client.get(f"/api/admin/documents/{doc['id']}/usage")
    assert response.status_code == 200, response.text
    return response.json()


def confirmed_delete(client, doc, snapshot=None):
    snapshot = snapshot or usage(client, doc)
    return client.delete(
        f"/api/admin/documents/{doc['id']}", params={"unlink": "true", "revision": snapshot["revision"]}
    )


def test_group_unassignment_keeps_document_and_other_groups_and_nas_permission(setup):
    app, client, _ = setup
    db = app.state.db
    first, second = db.all("group")[:2]
    doc = upload(client)
    assign(client, first, doc)
    assign(client, second, doc)
    response = client.delete(f"/api/admin/documents/{doc['id']}/groups/{first['id']}")
    assert response.status_code == 200
    assert response.json()["plan_id"] is None
    assert response.json()["plan_public"] is False
    assert db.get("document", doc["id"]) == doc
    assert db.get("group", second["id"])["plan_id"] == doc["id"]
    db.mutate("group", second["id"], {"plan_path": "Parents.pdf"})
    response = client.put(f"/api/admin/groups/{second['id']}/plan/none")
    assert response.status_code == 200
    assert response.json()["plan_id"] is None
    assert response.json()["plan_public"] is True
    assert response.json()["plan_path"] == "Parents.pdf"
    assert client.put(f"/api/admin/groups/{second['id']}/plan/none").json() == response.json()


def test_unassignment_does_not_remove_a_replacement_document(setup):
    app, client, _ = setup
    group = app.state.db.all("group")[0]
    first, second = upload(client), upload(client, "Other", "green")
    assign(client, group, first)
    assign(client, group, second)
    response = client.delete(f"/api/admin/documents/{first['id']}/groups/{group['id']}")
    assert response.status_code == 409
    assert app.state.db.get("group", group["id"])["plan_id"] == second["id"]


def test_confirmed_delete_clears_all_references_and_keeps_valid_time_settings(setup):
    app, client, _ = setup
    db = app.state.db
    group = db.all("group")[0]
    doc, other = upload(client), upload(client, "Other", "green")
    assign(client, group, doc)
    device, _ = pair_device(
        client,
        group,
        settings={
            "default_mode": "plan",
            "document_id": doc["id"],
            "content_windows_enabled": False,
            "content_windows": [window("plan", document_id=doc["id"], name="Lunch")],
            "playlist": [{"mode": "plan", "document_id": doc["id"], "seconds": 20}],
        },
    )
    db.mutate("device", device["id"], {"manual": {"mode": "plan", "until": None}})
    snapshot = usage(client, doc)
    assert len(snapshot["references"]) == 4
    url = f"/api/admin/documents/{doc['id']}"
    assert client.delete(url).status_code == 409
    assert client.delete(url, params={"unlink": True}).status_code == 409
    assert usage(client, doc) == snapshot
    response = confirmed_delete(client, doc, snapshot)
    assert response.status_code == 200, response.text
    assert response.json()["unlinked"] == 4
    assert db.get("document", doc["id"]) is None
    assert db.get("document", other["id"]) == other
    assert db.get("group", group["id"])["plan_id"] is None
    actual = db.get("device", device["id"])
    settings = Settings.model_validate(actual["settings"]).model_dump()
    assert settings["content_windows_enabled"] is False
    assert settings["content_windows"][0]["start"] == device["settings"]["content_windows"][0]["start"]
    assert settings["content_windows"][0]["mode"] == "photos"
    assert settings["default_mode"] == "photos"
    assert settings["playlist"] == [{"mode": "photos", "seconds": 12, "document_id": None}]
    assert actual["manual"] is None
    assert document_references(settings) == set()


def test_deleting_notice_image_keeps_message_text(setup):
    app, client, _ = setup
    doc = client.post(
        "/api/admin/upload/image", files={"file": ("photo.jpg", image_bytes(), "image/jpeg")}
    ).json()
    notice = client.put(
        "/api/admin/notices/new",
        json={
            "title": "Hello",
            "text": "Keep this message",
            "image_id": doc["id"],
        },
    ).json()
    assert usage(client, doc)["references"][0]["kind"] == "notice"
    assert confirmed_delete(client, doc).status_code == 200
    updated = app.state.db.get("notice", notice["id"])
    assert updated["text"] == "Keep this message"
    assert updated["image_id"] is None


def test_new_assignment_requires_a_new_confirmation(setup):
    app, client, _ = setup
    doc = upload(client)
    snapshot = usage(client, doc)
    assert snapshot["references"] == []
    group = app.state.db.all("group")[0]
    assign(client, group, doc)
    assert confirmed_delete(client, doc, snapshot).status_code == 409
    assert app.state.db.get("group", group["id"])["plan_id"] == doc["id"]
    assert app.state.db.get("document", doc["id"])
    assert confirmed_delete(client, doc).status_code == 200


def test_deletion_rolls_back_every_change_on_failure(setup, monkeypatch):
    app, client, _ = setup
    db = app.state.db
    groups = db.all("group")[:2]
    doc = upload(client)
    for group in groups:
        assign(client, group, doc)
    snapshot = usage(client, doc)
    original = Database.write
    calls = 0

    def fail_second(connection, kind, obj):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated database failure")
        original(connection, kind, obj)

    monkeypatch.setattr(Database, "write", staticmethod(fail_second))
    with pytest.raises(RuntimeError, match="simulated database failure"):
        confirmed_delete(client, doc, snapshot)
    assert usage(client, doc) == snapshot
    assert db.get("document", doc["id"]) == doc


def test_unreferenced_document_delete_and_access_checks(setup):
    app, client, _ = setup
    doc = upload(client)
    assert client.delete(f"/api/admin/documents/{doc['id']}").status_code == 200
    assert client.get(f"/api/admin/documents/{doc['id']}/usage").status_code == 404
    doc = upload(client)
    group = app.state.db.all("group")[0]
    assign(client, group, doc)
    snapshot = usage(client, doc)
    del client.headers["X-CSRF-Token"]
    assert confirmed_delete(client, doc, snapshot).status_code == 403
    assert client.delete(f"/api/admin/documents/{doc['id']}/groups/{group['id']}").status_code == 403
    client.cookies.clear()
    assert client.get(f"/api/admin/documents/{doc['id']}/usage").status_code == 401


def test_bulk_assignment_and_removal_preserve_documents_direct_uses_and_nas(setup):
    app, client, _ = setup
    db = app.state.db
    groups = db.all("group")
    doc, other = upload(client), upload(client, "Other", "green")
    assign(client, groups[0], other)
    db.mutate("group", groups[1]["id"], {"plan_path": "Internal.pdf", "plan_public": False})
    device, _ = pair_device(client, groups[0], settings={"default_mode": "plan", "document_id": doc["id"]})
    path = f"/api/admin/documents/{doc['id']}/groups"
    response = client.put(path, json={"plan_public": True})
    assert response.status_code == 200
    assert set(response.json()["groups"]) == {g["id"] for g in groups}
    assert all(g["plan_id"] == doc["id"] for g in db.all("group"))
    assert db.get("group", groups[0]["id"])["plan_public"] is True
    assert db.get("group", groups[1]["id"])["plan_public"] is False
    assert db.get("group", groups[1]["id"])["plan_path"] == "Internal.pdf"
    # A different document assigned since opening the dialog must not be removed.
    assign(client, groups[2], other)
    response = client.delete(path)
    assert response.status_code == 200
    assert set(response.json()["groups"]) == {g["id"] for g in groups[:2]}
    assert db.get("group", groups[0]["id"])["plan_id"] is None
    assert db.get("group", groups[0]["id"])["plan_public"] is False
    assert db.get("group", groups[1]["id"])["plan_path"] == "Internal.pdf"
    assert db.get("group", groups[2]["id"])["plan_id"] == other["id"]
    assert db.get("document", doc["id"]) == doc
    assert db.get("document", other["id"]) == other
    assert db.get("device", device["id"]) == device
    assert client.delete(path).json()["groups"] == []


@pytest.mark.parametrize("method", ["put", "delete"])
def test_bulk_group_assignment_is_atomic(setup, monkeypatch, method):
    app, client, _ = setup
    db = app.state.db
    doc = upload(client)
    if method == "delete":
        for group in db.all("group"):
            assign(client, group, doc)
    before = db.all("group")
    original = Database.write
    calls = 0

    def fail_second(connection, kind, obj):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated database failure")
        original(connection, kind, obj)

    monkeypatch.setattr(Database, "write", staticmethod(fail_second))
    with pytest.raises(RuntimeError, match="simulated database failure"):
        client.request(method.upper(), f"/api/admin/documents/{doc['id']}/groups", json={"plan_public": True})
    assert db.all("group") == before
    assert db.get("document", doc["id"]) == doc


def test_bulk_group_assignment_validates_document_and_admin_access(setup):
    app, client, _ = setup
    before = app.state.db.all("group")
    image = client.post("/api/admin/upload/image", files={"file": ("Image.jpg", image_bytes())}).json()
    for method in ("PUT", "DELETE"):
        assert client.request(method, "/api/admin/documents/missing/groups", json={}).status_code == 404
        assert (
            client.request(method, f"/api/admin/documents/{image['id']}/groups", json={}).status_code == 422
        )
    doc = upload(client)
    path = f"/api/admin/documents/{doc['id']}/groups"
    del client.headers["X-CSRF-Token"]
    assert client.put(path, json={}).status_code == 403
    assert client.delete(path).status_code == 403
    client.cookies.clear()
    assert client.put(path, json={}).status_code == 401
    assert client.delete(path).status_code == 401
    assert app.state.db.all("group") == before
