import io
import zipfile

from fastapi.testclient import TestClient
from PIL import Image, PngImagePlugin

from server.app import create_app
from server.branding import MAX_LOGO_BYTES
from server.config import Config
from server.manage import backup, restore
from shared.source import ROOT_FILES, source_archive


def png_logo(size=(1000, 500)):
    buffer = io.BytesIO()
    image = Image.new("RGBA", size, (36, 104, 98, 100))
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("private-note", "must-not-be-published")
    image.save(buffer, "PNG", pnginfo=metadata)
    return buffer.getvalue()


def upload(client, data):
    # The original filename and declared MIME type are never trusted or stored.
    return client.post("/api/admin/branding/logo", files={"file": ("../../private.png", data, "image/png")})


def test_public_defaults_and_admin_authorization(setup):
    app, client, _ = setup
    with TestClient(app) as visitor:
        result = visitor.get("/api/branding")
        assert set(result.json()) == {"name", "custom_logo", "logo_url"}
        assert result.json()["name"] == "Unsere Kita"
        assert not result.json()["custom_logo"]
        logo = visitor.get(result.json()["logo_url"])
        assert logo.headers["content-type"].startswith("image/svg+xml")
        assert "no-store" in logo.headers["cache-control"]
        assert visitor.get("/static/kita-logo.png").status_code == 404
        assert visitor.put("/api/admin/branding", json={"name": "Kita"}).status_code == 401
        assert upload(visitor, png_logo()).status_code == 401
        assert visitor.delete("/api/admin/branding/logo").status_code == 401
    client.headers.pop("X-CSRF-Token")
    assert upload(client, png_logo()).status_code == 403
    assert client.put("/api/admin/branding", json={"name": "Kita"}).status_code == 403
    assert client.delete("/api/admin/branding/logo").status_code == 403


def test_logo_name_restart_backup_and_reset(setup, tmp_path):
    app, client, config = setup
    before = client.get("/api/branding").json()
    response = upload(client, png_logo())
    assert response.status_code == 200, response.text
    assert response.json()["custom_logo"]
    assert response.json()["logo_url"] != before["logo_url"]
    normalized = client.get(response.json()["logo_url"])
    assert normalized.headers["content-type"] == "image/png"
    image = Image.open(io.BytesIO(normalized.content))
    assert image.size == (512, 256)
    assert image.mode == "RGBA"
    assert image.getpixel((10, 10))[3] == 100
    assert "private-note" not in image.info
    assert b"must-not-be-published" not in normalized.content
    renamed = client.put("/api/admin/branding", json={"name": "  Kita Sonnenblume  "})
    assert renamed.json()["name"] == "Kita Sonnenblume"
    assert renamed.json()["logo_url"] == response.json()["logo_url"]
    assert client.get("/api/admin/state").json()["branding"] == renamed.json()
    for name in (" ", "x" * 81, "line\nbreak"):
        assert client.put("/api/admin/branding", json={"name": name}).status_code == 422
    assert client.put("/api/admin/branding", json={"name": "Kita", "logo": "bad"}).status_code == 422
    with TestClient(create_app(config)) as restarted:
        assert restarted.get("/api/branding").json() == renamed.json()
        assert restarted.get("/api/branding/logo").content == normalized.content
    archive = backup(config, tmp_path / "backup.zip")
    recovered_config = Config(tmp_path / "restored", config.nas_root, background_scan=False)
    restore(recovered_config, archive)
    with TestClient(create_app(recovered_config)) as recovered:
        assert recovered.get("/api/branding").json() == renamed.json()
        assert recovered.get("/api/branding/logo").content == normalized.content
    reset = client.delete("/api/admin/branding/logo")
    assert reset.json() == {**before, "name": "Kita Sonnenblume"}
    assert app.state.db.get("branding", "site")["logo"] is None


def test_invalid_upload_keeps_previous_logo(setup):
    _, client, _ = setup
    assert upload(client, png_logo()).status_code == 200
    before = client.get("/api/branding/logo").content
    for data in (b"", b"not an image", b'<svg xmlns="http://www.w3.org/2000/svg"/>', png_logo((2001, 2000))):
        assert upload(client, data).status_code == 422
        assert client.get("/api/branding/logo").content == before
    assert upload(client, b"x" * (MAX_LOGO_BYTES + 1)).status_code == 413
    assert upload(client, b"x" * (MAX_LOGO_BYTES + 65537)).status_code == 413
    assert client.get("/api/branding/logo").content == before


def test_public_source_and_license_do_not_include_operator_data(setup):
    app, client, _ = setup
    assert upload(client, png_logo()).status_code == 200
    assert client.put("/api/admin/branding", json={"name": "Private-Test-Kita-8391"}).status_code == 200
    private_logo = app.state.db.get("branding", "site")["logo"]
    with TestClient(app) as visitor:
        license_response = visitor.get("/api/license")
        assert license_response.status_code == 200
        assert "AGPL-3.0-only" in license_response.text
        assert "WITHOUT ANY WARRANTY" in license_response.text
        response = visitor.get("/api/source")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            names = archive.namelist()
            assert "kitafenster/LICENSE" in names
            assert "kitafenster/server/static/default-logo.svg" in names
            assert "kitafenster/server/static/kita-logo.png" not in names
            assert not any(name.endswith((".sqlite3", ".jpg")) for name in names)
            assert not any(name.endswith(".png") and "/docs/screenshots/" not in name for name in names)
            for name in names:
                assert private_logo.encode() not in archive.read(name)
            # Inspect configuration-specific data only in the files offered as the app itself.
            assert b"Private-Test-Kita-8391" not in archive.read("kitafenster/server/static/index.html")


def test_source_selection_excludes_runtime_and_hidden_files(tmp_path):
    for name in ROOT_FILES:
        (tmp_path / name).write_text("source", encoding="utf-8")
    for name in ("server/app.py", "server/static/default-logo.svg", "deploy/player.example.json"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("source", encoding="utf-8")
    for name in (
        "data/secret.py",
        "demo-nas/private.svg",
        ".git/config",
        "dist/old.zip",
        "server/.private/secret.py",
        "server/static/actual-kita.png",
        "server/local.sqlite3",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("DO-NOT-PUBLISH", encoding="utf-8")
    with zipfile.ZipFile(io.BytesIO(source_archive(tmp_path))) as archive:
        assert all(b"DO-NOT-PUBLISH" not in archive.read(name) for name in archive.namelist())
        assert archive.read("kitafenster/deploy/player.example.json") == b"source"
