import json
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.config import Config
from server.manage import main, set_admin
from server.security import password_matches


@pytest.fixture
def admin_config(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NAS_ROOT", str(tmp_path / "nas"))
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    return replace(Config.from_env(), background_scan=False)


def account(app):
    with app.state.db.connect() as db:
        row = db.execute("SELECT data FROM auth WHERE key='admin'").fetchone()
    return json.loads(row[0]) if row else None


@pytest.mark.parametrize("password", ["", "x", "  ö🔑 $HOME # ' \\", "x" * 513])
def test_environment_bootstraps_login_with_any_password(admin_config, monkeypatch, password, capsys):
    monkeypatch.setenv("ADMIN_PASSWORD", password)
    config = replace(Config.from_env(), background_scan=False)
    assert "admin_password=" not in repr(config)
    app = create_app(config)
    stored = account(app)
    assert stored["username"] == "admin"
    assert stored["password"] != password
    assert password_matches(password, stored["password"])
    with TestClient(app) as client:
        response = client.post("/api/login", json={"username": "admin", "password": password})
        assert response.status_code == 200
        assert client.get("/api/admin/state").status_code == 200
        if not password:
            from html.parser import HTMLParser

            class Inputs(HTMLParser):
                def handle_starttag(self, tag, attrs):
                    if tag == "input" and dict(attrs).get("name") == "password":
                        assert "required" not in dict(attrs)

            Inputs().feed(client.get("/").text)
    assert not capsys.readouterr().out


def test_missing_password_does_not_create_default_account(admin_config):
    app = create_app(admin_config)
    assert account(app) is None
    with TestClient(app) as client:
        response = client.post("/api/login", json={"username": "admin", "password": ""})
        assert response.status_code == 503
        assert "ADMIN_PASSWORD" in response.json()["detail"]


@pytest.mark.parametrize("password_after_restart", ["x", None])
def test_restart_keeps_sessions_when_credentials_unchanged_or_unset(admin_config, password_after_restart):
    config = replace(admin_config, admin_password="x")
    app = create_app(config)
    with TestClient(app) as client:
        assert client.post("/api/login", json={"username": "admin", "password": "x"}).status_code == 200
        cookies = dict(client.cookies)
    original = account(app)
    restarted = create_app(replace(config, admin_password=password_after_restart))
    assert account(restarted) == original
    with TestClient(restarted) as client:
        client.cookies.update(cookies)
        assert client.get("/api/session").status_code == 200


@pytest.mark.parametrize("username,password", [("admin", "y"), ("neu", "x"), ("admin", "")])
def test_changed_environment_replaces_login_and_invalidates_old_sessions(admin_config, username, password):
    app = create_app(replace(admin_config, admin_password="x"))
    with TestClient(app) as client:
        assert client.post("/api/login", json={"username": "admin", "password": "x"}).status_code == 200
        cookies = dict(client.cookies)
    restarted = create_app(replace(admin_config, admin_username=username, admin_password=password))
    with TestClient(restarted) as client:
        client.cookies.update(cookies)
        assert client.get("/api/session").status_code == 401
        assert client.post("/api/login", json={"username": "admin", "password": "x"}).status_code == 401
        assert client.post("/api/login", json={"username": username, "password": password}).status_code == 200


def test_cli_uses_environment_without_prompting(admin_config, monkeypatch, capsys):
    monkeypatch.setenv("ADMIN_USERNAME", "leitung")
    monkeypatch.setenv("ADMIN_PASSWORD", "x")
    monkeypatch.setattr("sys.argv", ["server.manage", "admin"])
    monkeypatch.setattr("builtins.input", lambda _: pytest.fail("Unexpected username prompt"))
    monkeypatch.setattr("getpass.getpass", lambda _: pytest.fail("Unexpected password prompt"))
    main()
    app = create_app(admin_config)
    assert account(app)["username"] == "leitung"
    assert password_matches("x", account(app)["password"])
    assert "Administratorkonto gespeichert" in capsys.readouterr().out


@pytest.mark.parametrize("password", ["", "ö🔑"])
def test_interactive_cli_accepts_empty_and_unicode_passwords(admin_config, monkeypatch, password):
    monkeypatch.setattr("sys.argv", ["server.manage", "admin"])
    monkeypatch.setattr("builtins.input", lambda _: "")
    monkeypatch.setattr("getpass.getpass", lambda _: password)
    main()
    assert password_matches(password, account(create_app(admin_config))["password"])


def test_interactive_cli_still_rejects_mismatched_confirmation(admin_config, monkeypatch):
    monkeypatch.setattr("sys.argv", ["server.manage", "admin"])
    monkeypatch.setattr("builtins.input", lambda _: "")
    answers = iter(["x", "y"])
    monkeypatch.setattr("getpass.getpass", lambda _: next(answers))
    with pytest.raises(SystemExit, match="1"):
        main()
    assert account(create_app(admin_config)) is None


@pytest.mark.parametrize("username", ["", "x" * 81])
def test_invalid_username_is_rejected(admin_config, username):
    app = create_app(admin_config)
    with pytest.raises(ValueError, match="Benutzername"):
        set_admin(app.state.db, username, "x")
