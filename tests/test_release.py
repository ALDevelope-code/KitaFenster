import hashlib
from pathlib import Path
from zipfile import ZipFile

import pytest

from shared.source import ROOT_FILES
from tools.package_release import package_release
from tools.release_info import project_version, validate_tag


def test_release_bundles_versioned_nas_config_and_complete_source_without_local_data(tmp_path):
    root = Path(__file__).resolve().parents[1]
    for name in ROOT_FILES:
        (tmp_path / name).write_bytes((root / name).read_bytes())
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.2.3"\n', encoding="utf-8")
    for name in (
        "docs/INSTALLATION-NAS.md",
        "docs/INSTALLATION-PI.md",
        "docs/KURZANLEITUNG.md",
        "docs/BETRIEB.md",
        "docs/screenshots/01-uebersicht.png",
        ".github/workflows/container.yml",
        ".github/pull_request_template.md",
        "deploy/install-player.sh",
        "deploy/kita-player-kms.service",
        "deploy/samba-transfer.conf",
        "tools/check_nas.py",
        "server/static/default-logo.svg",
        "server/static/motion.js",
        "server/static/device-settings.js",
        "server/static/document-actions.js",
        "tests/motion_ui.test.cjs",
    ):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((root / name).read_bytes())
    (tmp_path / "data").mkdir()
    (tmp_path / "data/kita.sqlite3").write_text("PRIVATE-DATABASE", encoding="utf-8")
    (tmp_path / ".env").write_text("PRIVATE-CONFIGURATION", encoding="utf-8")
    source, nas, checksums = package_release(tmp_path, repository="OtherOwner/OtherKita")
    assert source.name == "kitafenster-1.2.3.zip"
    assert nas.name == "kitafenster-nas-1.2.3.zip"
    with ZipFile(source) as archive:
        assert "kitafenster/.github/workflows/container.yml" in archive.namelist()
        assert "kitafenster/.github/pull_request_template.md" in archive.namelist()
        assert "kitafenster/CONTRIBUTING.md" in archive.namelist()
        assert "kitafenster/SECURITY.md" in archive.namelist()
        assert "kitafenster/deploy/samba-transfer.conf" in archive.namelist()
        assert "kitafenster/deploy/kita-player-kms.service" in archive.namelist()
        assert "kitafenster/docs/KURZANLEITUNG.md" in archive.namelist()
        assert "kitafenster/docs/screenshots/01-uebersicht.png" in archive.namelist()
        assert "kitafenster/server/static/motion.js" in archive.namelist()
        assert "kitafenster/server/static/device-settings.js" in archive.namelist()
        assert "kitafenster/server/static/document-actions.js" in archive.namelist()
        assert "kitafenster/tests/motion_ui.test.cjs" in archive.namelist()
        assert b"\r" not in archive.read("kitafenster/deploy/install-player.sh")
        assert not any("/data/" in name or name.endswith("/.env") for name in archive.namelist())
    with ZipFile(nas) as archive:
        env = archive.read(".env.example").decode()
        assert "KITAFENSTER_VERSION=1.2.3" in env
        assert "KITAFENSTER_IMAGE=ghcr.io/otherowner/otherkita" in env
        assert set(archive.namelist()) == {
            "compose.yaml",
            ".env.example",
            "README.md",
            "docs/INSTALLATION-NAS.md",
            "docs/INSTALLATION-PI.md",
            "docs/KURZANLEITUNG.md",
            "docs/BETRIEB.md",
            "pruefe-nas.py",
            "LICENSE",
            "NOTICE",
        }
        assert archive.read("pruefe-nas.py") == (root / "tools/check_nas.py").read_bytes()
    for line in checksums.read_text().splitlines():
        expected, name = line.split("  ")
        assert hashlib.sha256((checksums.parent / name).read_bytes()).hexdigest() == expected


def test_release_rejects_mismatched_tag_and_unsafe_image_names(tmp_path):
    assert validate_tag("v1.2.3", "1.2.3") == "1.2.3"
    for tag in ("v1.2.4", "1.2.3", "v1.2.3-rc1", "v1.2.3\nextra", "v1.2.3; echo injected"):
        with pytest.raises(ValueError):
            validate_tag(tag, "1.2.3")
    with pytest.raises(ValueError):
        package_release(tmp_path, repository="owner/repo; command")
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.2.3-rc1"\n', encoding="utf-8")
    with pytest.raises(ValueError):
        project_version(tmp_path)
