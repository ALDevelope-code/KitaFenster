import zipfile
from pathlib import Path

import pytest
from conftest import image_bytes

from server.config import Config
from server.db import Database
from server.manage import backup, restore


def test_backup_restores_database_and_prepared_files(setup, tmp_path):
    app, _, config = setup
    ids = app.state.media.ingest(image_bytes(), ".jpg")
    app.state.db.put("document", {"id": "saved-upload", "assets": ids})
    archive = backup(config, tmp_path / "backup.zip")
    restored = Config(tmp_path / "restored", config.nas_root)
    restore(restored, archive)
    assert Database(restored.data_dir / "kita.sqlite3").all("group") == app.state.db.all("group")
    assert (restored.data_dir / "assets" / (ids[0] + ".jpg")).read_bytes() == (
        config.data_dir / "assets" / (ids[0] + ".jpg")
    ).read_bytes()
    with pytest.raises(ValueError):
        restore(restored, archive)


def test_backup_excludes_orphans_even_before_sweep(setup, tmp_path):
    app, _, config = setup
    db = app.state.db
    group = db.all("group")[0]
    (config.nas_root / group["folder"] / "Foto.jpg").write_bytes(image_bytes())
    app.state.media.scan()
    photo = db.get("snapshot", group["id"])["photos"][0]
    orphan_id = "d" * 64
    (config.data_dir / "assets" / (orphan_id + ".jpg")).write_bytes(image_bytes())
    db.put("asset", {"id": orphan_id, "sha256": orphan_id, "bytes": 1, "width": 1, "height": 1})
    archive = backup(config, tmp_path / "race.zip")
    with zipfile.ZipFile(archive) as zip_file:
        names = zip_file.namelist()
    # No cleanup is necessary to exclude unreferenced processing leftovers.
    assert "assets/" + photo + ".jpg" in names
    assert "assets/" + orphan_id + ".jpg" not in names
    assert (config.data_dir / "assets" / (orphan_id + ".jpg")).exists()


def test_restore_rejects_archive_path_escape(tmp_path):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("kita.sqlite3", b"dummy")
        z.writestr("../outside", b"bad")
    with pytest.raises(ValueError):
        restore(Config(tmp_path / "restored", Path("nas")), archive)
    assert not (tmp_path / "outside").exists()
