"""Betriebsbefehle. Zugangsdaten aus der Umgebung oder verdeckter Passwortabfrage."""

import argparse
import getpass
import os
import secrets
import shutil
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path

from server.assets import asset_lock, required_asset_files
from server.config import Config
from server.db import Database
from server.security import set_admin


def backup(config, destination):
    db = Database(config.data_dir / "kita.sqlite3")
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise ValueError("Zieldatei existiert bereits")
    with (
        asset_lock(config.data_dir),
        tempfile.TemporaryDirectory(dir=destination.parent, prefix=".kitafenster-backup-") as temporary,
    ):
        snapshot = Path(temporary) / "kita.sqlite3"
        with db.connect() as source, closing(sqlite3.connect(snapshot)) as target:
            source.backup(target)
        paths = required_asset_files(Database(snapshot), config.data_dir / "assets")
        temp_zip = Path(temporary) / "backup.zip"
        with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(snapshot, "kita.sqlite3")
            for asset in paths:
                archive.write(asset, "assets/" + asset.name)
        os.replace(temp_zip, destination)
    return destination


def restore(config, archive_path):
    """Nur in gestopptem Dienst und in ein leeres Datenverzeichnis zurückspielen."""
    if config.data_dir.exists() and any(config.data_dir.iterdir()):
        raise ValueError(
            "Wiederherstellung benötigt ein leeres Datenverzeichnis. Vorhandene Daten vorher sichern und umbenennen."
        )
    from player.cache import ASSET_ID

    config.data_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if "kita.sqlite3" not in names:
            raise ValueError("Datenbank fehlt im Archiv")
        for name in names:
            if name != "kita.sqlite3" and not (
                name.startswith("assets/") and name.endswith(".jpg") and ASSET_ID.fullmatch(name[7:-4])
            ):
                raise ValueError("Unerwarteter Pfad im Archiv")
        if archive.testzip():
            raise ValueError("Archiv ist beschädigt")
        # Check the database before publishing restored files.
        with tempfile.TemporaryDirectory(dir=config.data_dir) as temporary:
            temp = Path(temporary)
            for name in names:
                output = temp / name
                output.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as source, output.open("wb") as target:
                    shutil.copyfileobj(source, target)
            with closing(sqlite3.connect(temp / "kita.sqlite3")) as check:
                if check.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("Datenbankprüfung fehlgeschlagen")
            required_asset_files(Database(temp / "kita.sqlite3"), temp / "assets")
            if (temp / "assets").exists():
                shutil.move(str(temp / "assets"), str(config.data_dir / "assets"))
            os.replace(temp / "kita.sqlite3", config.data_dir / "kita.sqlite3")


def demo(config):
    """Explizite lokale Beispieldaten ohne simulierte Geräte-Verbindungen."""
    from PIL import Image, ImageDraw, ImageFont

    from server.app import create_app
    from server.db import uid
    from server.models import Settings

    app = create_app(config)
    db = app.state.db
    if db.all("device"):
        raise ValueError("Demo nur in einem Projekt ohne registrierte Geräte ausführen")
    config.nas_root.mkdir(parents=True, exist_ok=True)
    (config.nas_root / ".bilderrahmen-source").touch()
    colors = [
        ("#b3c9b5", "#436c59", "#ecc575"),
        ("#c1d8db", "#3e7180", "#f2d993"),
        ("#d9c8ad", "#9a7456", "#f3dda2"),
    ]
    for index, group in enumerate(sorted(db.all("group"), key=lambda g: g["name"])):
        folder = config.nas_root / group["folder"]
        folder.mkdir(exist_ok=True)
        for photo in range(3):
            bg, foreground, sun = colors[index % 3]
            img = Image.new("RGB", (1280, 720), bg)
            draw = ImageDraw.Draw(img)
            draw.ellipse((800 - photo * 100, 90, 970 - photo * 100, 260), fill=sun)
            draw.ellipse((-200, 330 + photo * 40, 1000, 1200), fill=foreground)
            draw.ellipse((700, 450, 1600, 1000), fill=bg)
            try:
                face = ImageFont.truetype("DejaVuSans.ttf", 30)
            except OSError:
                face = ImageFont.load_default(size=30)
            draw.text((60, 640), "Beispielmotiv · " + group["name"], fill="white", font=face)
            img.save(folder / f"Beispiel-{photo + 1}.jpg")
        db.put(
            "device",
            {
                "id": uid(),
                "name": "Vorraum " + group["name"],
                "group_id": group["id"],
                "allow_internal": False,
                "settings": Settings().model_dump(),
                "manual": None,
                "last_seen": None,
                "reported": {},
            },
        )
    db.put(
        "notice",
        {
            "id": uid(),
            "title": "Schön, dass ihr da seid.",
            "text": "Hier teilen wir kleine Einblicke in unseren Kita-Alltag.\nWir freuen uns auf einen schönen Tag mit euch!",
            "target": {"kind": "all", "id": ""},
            "internal": False,
            "urgent": False,
            "theme": "ocean",
            "starts_at": None,
            "ends_at": None,
            "image_id": None,
        },
    )
    app.state.media.scan()


def main():
    parser = argparse.ArgumentParser(description="KitaFenster verwalten")
    parser.add_argument("command", choices=["admin", "backup", "restore", "demo"])
    parser.add_argument("path", nargs="?")
    args = parser.parse_args()
    config = Config.from_env()
    try:
        if args.command == "admin":
            username, password = config.admin_username, config.admin_password
            if password is None:
                username = input(f"Administrator-Benutzername [{username}]: ").strip() or username
                password = getpass.getpass("Neues Passwort: ")
                if not secrets.compare_digest(
                    password.encode(), getpass.getpass("Passwort wiederholen: ").encode()
                ):
                    raise ValueError("Passwörter stimmen nicht überein")
            set_admin(Database(config.data_dir / "kita.sqlite3"), username, password)
            print("Administratorkonto gespeichert; bisherige Sitzungen abgemeldet.")
        elif args.command == "demo":
            demo(config)
            print("Beispieldaten angelegt. Die Demo-Geräte sind offline, bis echte Player gekoppelt werden.")
        elif args.command == "backup":
            if not args.path:
                raise ValueError("Zielpfad für die ZIP-Sicherung fehlt")
            print("Sicherung erstellt:", backup(config, args.path))
        elif args.command == "restore":
            if not args.path:
                raise ValueError("Pfad der ZIP-Sicherung fehlt")
            restore(config, args.path)
            print("Sicherung wiederhergestellt.")
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
