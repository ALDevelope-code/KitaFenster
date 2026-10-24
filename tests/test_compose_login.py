import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(not shutil.which("docker"), reason="Docker Compose CLI not installed")
@pytest.mark.parametrize("password", [None, "", "x", '  ö🔑 $HOME # "  '])
def test_compose_passes_dotenv_password_literally_and_preserves_unset(tmp_path, password):
    root = Path(__file__).resolve().parents[1]
    shutil.copyfile(root / "compose.yaml", tmp_path / "compose.yaml")
    settings = "ADMIN_USERNAME=leitung\n"
    if password is not None:
        settings += f"ADMIN_PASSWORD='{password}'\n"
    (tmp_path / ".env").write_text(settings, encoding="utf-8")
    environment = {k: v for k, v in os.environ.items() if k not in {"ADMIN_USERNAME", "ADMIN_PASSWORD"}}
    result = subprocess.run(
        ["docker", "compose", "config", "--format", "json", "--no-path-resolution"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        encoding="utf-8",
        check=True,
        timeout=30,
    )
    actual = json.loads(result.stdout)["services"]["verwaltung"]["environment"]
    assert actual["ADMIN_USERNAME"] == "leitung"
    # `config` doubles dollar signs when rendering a reusable Compose document.
    expected = password.replace("$", "$$") if password is not None else None
    assert actual.get("ADMIN_PASSWORD") == expected


@pytest.mark.skipif(not shutil.which("docker"), reason="Docker Compose CLI not installed")
@pytest.mark.parametrize(
    "settings,user,groups",
    [
        ("", "10001:10001", ["10001"]),
        ("NAS_UID=1026\nNAS_GID=100\nNAS_READ_GID=101\n", "1026:100", ["101"]),
        ("NAS_UID=1033\nNAS_GID=100\nNAS_READ_GID=\n", "1033:100", ["100"]),
    ],
)
def test_compose_uses_nas_identity_and_preserves_read_only_source(tmp_path, settings, user, groups):
    root = Path(__file__).resolve().parents[1]
    shutil.copyfile(root / "compose.yaml", tmp_path / "compose.yaml")
    (tmp_path / ".env").write_text(settings, encoding="utf-8")
    environment = {k: v for k, v in os.environ.items() if k not in {"NAS_UID", "NAS_GID", "NAS_READ_GID"}}
    result = subprocess.run(
        ["docker", "compose", "config", "--format", "json", "--no-path-resolution"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        encoding="utf-8",
        check=True,
        timeout=30,
    )
    service = json.loads(result.stdout)["services"]["verwaltung"]
    assert service["user"] == user
    assert service["group_add"] == groups
    mounts = {mount["target"]: mount for mount in service["volumes"]}
    assert mounts["/nas"]["read_only"] is True
    assert not mounts["/data"].get("read_only", False)
