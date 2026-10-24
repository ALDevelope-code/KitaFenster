"""Einmalige lokale Entwicklungs-Vorschau, ausschließlich mit Beispieldaten."""

import json
import secrets

from server.app import create_app
from server.config import Config
from server.manage import demo, set_admin

config = Config.from_env()
app = create_app(config)
if not app.state.db.all("device"):
    demo(config)
password_path = config.data_dir / "preview-access.json"
if not password_path.exists():
    password = secrets.token_urlsafe(18)
    set_admin(app.state.db, "vorschau", password)
    password_path.write_text(json.dumps({"username": "vorschau", "password": password}), encoding="utf-8")
    password_path.chmod(0o600)
print("Vorschau vorbereitet. Zugang liegt lokal in data/preview-access.json.")
