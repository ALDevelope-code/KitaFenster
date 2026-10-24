from pathlib import Path

import pytest

from tools.release_info import ROOT, VERSION_FIELDS, check_versions, set_version, version_fields


@pytest.fixture
def version_tree(tmp_path):
    for name in VERSION_FIELDS:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / name).read_bytes())
    return tmp_path


def tree_bytes(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_setting_version_preserves_other_values_history_and_line_endings(version_tree):
    root = version_tree
    for index, name in enumerate(VERSION_FIELDS):
        path = root / name
        content = path.read_bytes().replace(b"\r\n", b"\n")
        if index % 2:
            content = content.replace(b"\n", b"\r\n")
        path.write_bytes(content)
    (root / ".env").write_bytes(b"KITAFENSTER_VERSION=0.0.9\r\nADMIN_PASSWORD=private\r\n")
    (root / "history.md").write_text("Sensor ab Version 0.1.2", encoding="utf-8")
    before = tree_bytes(root)
    fields = version_fields(root)
    assert set(set_version("2.10.3", root)) == set(VERSION_FIELDS)
    assert check_versions(root) == "2.10.3"
    for path, _, content, match in fields:
        start, end = match.span("version")
        assert path.read_bytes() == (content[:start] + "2.10.3" + content[end:]).encode("utf-8")
    after = tree_bytes(root)
    assert after[Path(".env")] == before[Path(".env")]
    assert after[Path("history.md")] == before[Path("history.md")]
    assert set_version("2.10.3", root) == []
    assert tree_bytes(root) == after


@pytest.mark.parametrize("version", ["v1.2.3", "1.2", "01.2.3", "1.2.3-rc1", "1.2.3\n"])
def test_invalid_versions_do_not_edit_files(version_tree, version):
    before = tree_bytes(version_tree)
    with pytest.raises(ValueError, match="drei Zahlen"):
        set_version(version, version_tree)
    assert tree_bytes(version_tree) == before


@pytest.mark.parametrize("damage", ["missing_file", "missing_slot", "duplicate_slot"])
def test_all_slots_are_checked_before_any_file_is_changed(version_tree, damage):
    path = version_tree / "server/app.py"
    if damage == "missing_file":
        path.unlink()
    elif damage == "missing_slot":
        path.write_text("# Health endpoint moved\n", encoding="utf-8")
    else:
        path.write_bytes(path.read_bytes() + b'\nreturn {"status": "ok", "version": "0.0.1"}\n')
    before = tree_bytes(version_tree)
    with pytest.raises((OSError, ValueError)):
        set_version("3.0.0", version_tree)
    assert tree_bytes(version_tree) == before


def test_check_detects_drift_and_set_repairs_it(version_tree):
    set_version("1.2.3", version_tree)
    path = version_tree / "Dockerfile"
    path.write_bytes(path.read_bytes().replace(b"APP_VERSION=1.2.3", b"APP_VERSION=1.2.2"))
    with pytest.raises(ValueError, match="Dockerfile"):
        check_versions(version_tree)
    assert set_version("1.2.3", version_tree) == ["Dockerfile"]
    assert check_versions(version_tree) == "1.2.3"


def test_write_failure_restores_already_edited_files(version_tree, monkeypatch):
    before = tree_bytes(version_tree)
    write = Path.write_bytes
    failed = False

    def failing_write(path, content):
        nonlocal failed
        if path.name == "Dockerfile" and not failed:
            failed = True
            write(path, b"partial write")
            raise OSError("Disk write failed")
        return write(path, content)

    monkeypatch.setattr(Path, "write_bytes", failing_write)
    with pytest.raises(OSError, match="Disk write failed"):
        set_version("5.0.0", version_tree)
    assert tree_bytes(version_tree) == before


def test_repository_versions_are_consistent():
    assert check_versions()
