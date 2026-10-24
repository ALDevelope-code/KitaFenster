"""Start a disposable Docker container with production restrictions and verify it."""

import argparse
import base64
import http.cookiejar
import io
import json
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from uuid import uuid4


def docker(*args):
    return subprocess.run(
        ["docker", *args], check=True, text=True, capture_output=True, timeout=120
    ).stdout.strip()


def check_container(image):
    name = "kitafenster-smoke-" + uuid4().hex
    volume = name + "-data"
    created = False
    started = False
    try:
        with tempfile.TemporaryDirectory(prefix=name) as temporary:
            nas = Path(temporary) / "nas"
            nas.mkdir(mode=0o755)
            (nas / ".bilderrahmen-source").touch()
            # A neutral one-pixel PNG, generated solely for this isolated test.
            sample = base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aN1kAAAAASUVORK5CYII="
            )
            for index in range(1, 4):
                folder = nas / f"Gruppe {index}"
                folder.mkdir(mode=0o755)
                (folder / "sample.png").write_bytes(sample)
            docker("volume", "create", volume)
            created = True
            # The environment bootstraps a short password in this disposable volume.
            password = "x"
            docker(
                "run",
                "--detach",
                "--name",
                name,
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges:true",
                "--memory=768m",
                "--tmpfs=/tmp:size=128m",
                "--mount",
                f"type=volume,source={volume},target=/data",
                "--mount",
                f"type=bind,source={nas},target=/nas,readonly",
                "--publish",
                "127.0.0.1::8088",
                "--env",
                "ADMIN_USERNAME=smoke",
                "--env",
                "ADMIN_PASSWORD=" + password,
                image,
            )
            started = True
            port = json.loads(docker("inspect", "--format", "{{json .NetworkSettings.Ports}}", name))[
                "8088/tcp"
            ][0]["HostPort"]
            base = f"http://127.0.0.1:{port}"
            client = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
            )
            csrf = ""

            def request(path, body=None, method=None):
                headers = {"Content-Type": "application/json", "X-CSRF-Token": csrf}
                req = urllib.request.Request(
                    base + path,
                    data=None if body is None else json.dumps(body).encode(),
                    headers=headers,
                    method=method,
                )
                with client.open(req, timeout=5) as response:
                    return response.read()

            def ready():
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    try:
                        if json.loads(request("/api/health"))["status"] == "ok":
                            return
                    except (OSError, ValueError):
                        time.sleep(1)
                raise AssertionError("Container did not become ready in 60 seconds")

            ready()
            assert docker("exec", name, "id", "-u") == "10001"
            try:
                request("/api/admin/state")
                raise AssertionError("Admin state unexpectedly public")
            except urllib.error.HTTPError as error:
                assert error.code == 401
            assert "custom_logo" in json.loads(request("/api/branding"))
            assert b"GNU AFFERO GENERAL PUBLIC LICENSE" in request("/api/license")
            with zipfile.ZipFile(io.BytesIO(request("/api/source"))) as archive:
                names = archive.namelist()
                assert "kitafenster/.github/workflows/container.yml" in names
                assert "kitafenster/deploy/install-player.sh" in names
                assert not any(n.endswith((".sqlite3", "sample.png")) or "/data/" in n for n in names)
            csrf = json.loads(request("/api/login", {"username": "smoke", "password": password}))["csrf"]
            request("/api/admin/scan", {}, "POST")
            state = json.loads(request("/api/admin/state"))
            assert len(state["snapshots"]) == 3
            assert all(len(snapshot["photos"]) == 1 for snapshot in state["snapshots"]), state["snapshots"]
            request("/api/admin/branding", {"name": "Container test"}, "PUT")
            docker("restart", name)
            port = json.loads(docker("inspect", "--format", "{{json .NetworkSettings.Ports}}", name))[
                "8088/tcp"
            ][0]["HostPort"]
            base = f"http://127.0.0.1:{port}"
            ready()
            assert json.loads(request("/api/branding"))["name"] == "Container test"
            assert json.loads(request("/api/session"))["csrf"] == csrf
            print(
                "Container OK: non-root, read-only root/NAS, authenticated scan, source offer, persistent database."
            )
    except Exception:
        if started:
            subprocess.run(["docker", "logs", "--tail", "80", name], check=False, timeout=15)
        raise
    finally:
        # Only resources named for this invocation are removed.
        if started:
            docker("rm", "--force", name)
        if created:
            docker("volume", "rm", volume)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    check_container(parser.parse_args().image)
