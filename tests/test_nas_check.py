from pathlib import Path

import pytest

from tools.check_nas import check_access, main


@pytest.fixture
def folders(tmp_path):
    nas, data = tmp_path / "nas", tmp_path / "data"
    nas.mkdir()
    data.mkdir()
    (nas / ".bilderrahmen-source").touch()
    group = nas / "Gruppe 1"
    (group / "Bilder").mkdir(parents=True)
    (group / "Bilder/foto.JPG").write_bytes(b"file read test")
    (group / "plan.pdf").write_bytes(b"file read test")
    (group / "@eaDir").mkdir()
    (group / "@eaDir/preview.jpg").touch()
    return nas, data


def test_checks_nested_media_and_cleans_write_probe(folders, capsys):
    nas, data = folders
    check_access(nas, data, ["Gruppe 1"])
    output = capsys.readouterr().out
    assert "Gruppe 1: 2 Bild-/PDF-Dateien lesbar" in output
    assert "Schreiben erfolgreich" in output
    assert list(data.iterdir()) == []


@pytest.mark.parametrize("missing", ["marker", "group", "data"])
def test_missing_mount_or_group_is_an_error(folders, missing):
    nas, data = folders
    groups = ["Gruppe 1"]
    if missing == "marker":
        (nas / ".bilderrahmen-source").unlink()
    elif missing == "group":
        groups = ["Nicht vorhanden"]
    else:
        data.rmdir()
    with pytest.raises(FileNotFoundError):
        check_access(nas, data, groups)


def test_unreadable_photo_stops_check(folders, monkeypatch, capsys):
    nas, data = folders
    original = Path.open

    def open_file(path, *args, **kwargs):
        if path.suffix == ".JPG":
            raise PermissionError("Foto nicht lesbar")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_file)
    with pytest.raises(PermissionError):
        check_access(nas, data, ["Gruppe 1"])
    assert "Schreiben erfolgreich" not in capsys.readouterr().out


def test_cli_returns_failure_for_nonwritable_data(folders, monkeypatch, capsys):
    nas, data = folders
    monkeypatch.setenv("NAS_ROOT", str(nas))
    monkeypatch.setenv("DATA_DIR", str(data))
    monkeypatch.setattr("sys.argv", ["check_nas", "Gruppe 1"])

    def denied(**kwargs):
        raise PermissionError("Datenordner nicht beschreibbar")

    monkeypatch.setattr("tools.check_nas.tempfile.TemporaryFile", denied)
    assert main() == 1
    assert "Datenordner nicht beschreibbar" in capsys.readouterr().err
