import os
import subprocess
import sys
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from conftest import image_bytes

from server.config import Config
from server.db import Database
from server.manage import backup, restore
from server.media import Media


@pytest.fixture
def storage(tmp_path):
    config = Config(tmp_path / "data", tmp_path / "nas", background_scan=False)
    db = Database(config.data_dir / "kita.sqlite3")
    media = Media(config, db)
    group = db.put("group", {"id": "group", "folder": "photos", "plan_path": "Plan.jpg"})
    (config.nas_root / "photos").mkdir(parents=True)
    (config.nas_root / ".bilderrahmen-source").touch()
    (config.nas_root / "photos" / "Foto.jpg").write_bytes(image_bytes())
    (config.nas_root / "photos" / "Plan.jpg").write_bytes(image_bytes("blue"))
    return config, db, media, group


@pytest.mark.parametrize("kind", ["photos", "plan"])
@pytest.mark.parametrize("damage", ["file", "descriptor", "truncated"])
def test_unchanged_source_repairs_missing_prepared_assets(storage, kind, damage):
    config, db, media, group = storage
    media.scan()
    original = db.get("snapshot", group["id"])
    id = original[kind][0]
    path = media.assets / (id + ".jpg")
    content = path.read_bytes()
    if damage == "file":
        path.unlink()
    elif damage == "descriptor":
        db.delete("asset", id)
    else:
        path.write_bytes(b"truncated")
    media.scan()
    result = db.get("snapshot", group["id"])
    assert not result["error"]
    assert result[kind] == original[kind]
    assert path.read_bytes() == content
    assert db.get("asset", id)["bytes"] == len(content)


def test_reused_upload_is_protected_until_document_is_published(setup, monkeypatch):
    app, client, _ = setup
    db, media = app.state.db, app.state.media
    id = media.ingest(image_bytes(), ".jpg")[0]
    path = media.assets / (id + ".jpg")
    os.utime(path, (time.time() - 600, time.time() - 600))
    publishing, release, sweeping = threading.Event(), threading.Event(), threading.Event()
    original_put = db.put

    def pause_publication(kind, value):
        if kind == "document":
            publishing.set()
            assert release.wait(10)
        return original_put(kind, value)

    def sweep():
        sweeping.set()
        media.sweep()

    monkeypatch.setattr(db, "put", pause_publication)
    with ThreadPoolExecutor(max_workers=2) as pool:
        upload = pool.submit(
            client.post, "/api/admin/upload/image", files={"file": ("Again.jpg", image_bytes())}
        )
        try:
            assert publishing.wait(10)
            cleanup = pool.submit(sweep)
            assert sweeping.wait(10)
            with pytest.raises(TimeoutError):
                cleanup.result(timeout=0.2)
        finally:
            release.set()
        response = upload.result(timeout=10)
        cleanup.result(timeout=10)
    assert response.status_code == 200, response.text
    assert response.json()["assets"] == [id]
    assert path.is_file() and db.get("asset", id)


def test_backup_protects_snapshot_files_against_another_process(storage, tmp_path, monkeypatch):
    config, db, media, _ = storage
    id = media.ingest(image_bytes(), ".jpg")[0]
    path = media.assets / (id + ".jpg")
    content = path.read_bytes()
    os.utime(path, (time.time() - 600, time.time() - 600))
    db.put("document", {"id": "document", "assets": [id]})
    ready = tmp_path / "sweep-ready"
    code = """
import sys
from pathlib import Path
from server.config import Config
from server.db import Database
from server.media import Media
config = Config(Path(sys.argv[1]), Path(sys.argv[2]), background_scan=False)
media = Media(config, Database(config.data_dir / 'kita.sqlite3'))
Path(sys.argv[3]).touch()
media.sweep()
"""
    children = []
    original_write = zipfile.ZipFile.write

    def delete_during_archive(archive, filename, arcname=None, *args, **kwargs):
        result = original_write(archive, filename, arcname, *args, **kwargs)
        if arcname == "kita.sqlite3":
            # The backup snapshot still needs this document, although the live DB does not.
            db.delete("document", "document")
            process = subprocess.Popen(
                [sys.executable, "-c", code, str(config.data_dir), str(config.nas_root), str(ready)],
                cwd=Path(__file__).resolve().parents[1],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            children.append(process)
            deadline = time.monotonic() + 10
            while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            assert ready.exists()
            with pytest.raises(subprocess.TimeoutExpired):
                process.communicate(timeout=0.2)
            assert path.is_file()
        return result

    monkeypatch.setattr(zipfile.ZipFile, "write", delete_during_archive)
    try:
        archive = backup(config, tmp_path / "backup.zip")
        for process in children:
            _, errors = process.communicate(timeout=10)
            assert process.returncode == 0, errors.decode()
        assert not path.exists()  # Sweep resumes after backup releases its lock.
        restored = Config(tmp_path / "restored", config.nas_root)
        restore(restored, archive)
        assert Database(restored.data_dir / "kita.sqlite3").get("document", "document")["assets"] == [id]
        assert (restored.data_dir / "assets" / path.name).read_bytes() == content
    finally:
        for process in children:
            if process.poll() is None:
                process.kill()
            process.communicate()


@pytest.mark.parametrize("damage", ["file", "descriptor", "truncated"])
def test_incomplete_backup_is_rejected_and_lock_released(storage, tmp_path, damage):
    config, db, media, _ = storage
    media.scan()
    id = db.all("snapshot")[0]["photos"][0]
    path = media.assets / (id + ".jpg")
    if damage == "file":
        path.unlink()
    elif damage == "descriptor":
        db.delete("asset", id)
    else:
        path.write_bytes(b"truncated")
    destination = tmp_path / "backup.zip"
    with pytest.raises(ValueError, match="unvollständig"):
        backup(config, destination)
    assert not destination.exists()
    assert not list(tmp_path.glob(".kitafenster-backup-*"))
    media.scan()
    assert backup(config, destination).is_file()


def test_restore_rejects_archive_with_missing_referenced_file(storage, tmp_path):
    config, _, media, _ = storage
    media.scan()
    archive = backup(config, tmp_path / "complete.zip")
    incomplete = tmp_path / "incomplete.zip"
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(incomplete, "w") as target:
        target.writestr("kita.sqlite3", source.read("kita.sqlite3"))
    restored = Config(tmp_path / "restored", config.nas_root)
    with pytest.raises(ValueError, match="unvollständig"):
        restore(restored, incomplete)
    assert not (restored.data_dir / "kita.sqlite3").exists()
    assert not (restored.data_dir / "assets").exists()
