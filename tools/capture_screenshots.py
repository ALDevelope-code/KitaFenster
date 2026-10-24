"""Capture the README screenshot set from a running local KitaFenster server.

Windows usage:
    python -m tools.capture_screenshots

The script uses Microsoft Edge's DevTools protocol directly and has no extra
Python dependencies. The demo server must already run on http://127.0.0.1:8088.
"""

import base64
import json
import os
import secrets
import socket
import struct
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "screenshots"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
PORT = 9223
BASE_URL = "http://127.0.0.1:8088"


class DevTools:
    def __init__(self, url):
        parsed = urlsplit(url)
        self.socket = socket.create_connection((parsed.hostname, parsed.port), timeout=10)
        key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        request = (
            f"GET {parsed.path} HTTP/1.1\r\n"
            f"Host: {parsed.netloc}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n"
            "Origin: http://localhost\r\n\r\n"
        )
        self.socket.sendall(request.encode("ascii"))
        response = self._until(b"\r\n\r\n")
        if b" 101 " not in response.split(b"\r\n", 1)[0]:
            raise RuntimeError("DevTools-WebSocket konnte nicht geöffnet werden")
        self.next_id = 0

    def _until(self, marker):
        data = b""
        while marker not in data:
            data += self.socket.recv(4096)
        return data

    def _read(self, size):
        data = b""
        while len(data) < size:
            chunk = self.socket.recv(size - len(data))
            if not chunk:
                raise ConnectionError("DevTools-Verbindung wurde geschlossen")
            data += chunk
        return data

    def _send_frame(self, payload):
        payload = payload.encode("utf-8")
        mask = secrets.token_bytes(4)
        length = len(payload)
        header = bytearray([0x81])
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self.socket.sendall(bytes(header) + mask + masked)

    def _receive_frame(self):
        first, second = self._read(2)
        opcode, length = first & 0x0F, second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._read(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read(8))[0]
        if second & 0x80:
            mask = self._read(4)
        else:
            mask = None
        payload = self._read(length)
        if mask:
            payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        if opcode == 0x9:
            self._send_frame(payload.decode("utf-8"))
            return self._receive_frame()
        if opcode == 0x8:
            raise ConnectionError("DevTools-Verbindung wurde geschlossen")
        return json.loads(payload.decode("utf-8"))

    def call(self, method, params=None):
        self.next_id += 1
        message_id = self.next_id
        self._send_frame(json.dumps({"id": message_id, "method": method, "params": params or {}}))
        while True:
            response = self._receive_frame()
            if response.get("id") == message_id:
                if "error" in response:
                    raise RuntimeError(response["error"]["message"])
                return response.get("result", {})

    def evaluate(self, expression):
        result = self.call(
            "Runtime.evaluate",
            {"expression": expression, "awaitPromise": True, "returnByValue": True},
        )
        if result.get("exceptionDetails"):
            raise RuntimeError(result["exceptionDetails"].get("text", "JavaScript-Fehler"))
        return result.get("result", {}).get("value")

    def screenshot(self, path):
        result = self.call("Page.captureScreenshot", {"format": "png", "fromSurface": True})
        path.write_bytes(base64.b64decode(result["data"]))


def wait_for_page(port):
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1) as response:
                pages = json.load(response)
            return next(
                page
                for page in pages
                if page.get("type") == "page" and page.get("url", "").startswith(BASE_URL)
            )
        except (OSError, StopIteration, urllib.error.URLError):
            time.sleep(0.2)
    raise RuntimeError("Microsoft Edge hat die DevTools-Schnittstelle nicht geöffnet")


def wait_ready(devtools, expression="document.readyState === 'complete'"):
    deadline = time.time() + 15
    while time.time() < deadline:
        if devtools.evaluate(expression):
            return
        time.sleep(0.15)
    raise RuntimeError("Die KitaFenster-Oberfläche wurde nicht rechtzeitig bereit")


def main():
    if os.name != "nt" or not EDGE.is_file():
        raise RuntimeError("Dieses Hilfsprogramm benötigt Microsoft Edge unter Windows")
    try:
        urllib.request.urlopen(BASE_URL + "/api/health", timeout=2).close()
    except OSError as error:
        raise RuntimeError("KitaFenster muss zuerst lokal auf Port 8088 gestartet werden") from error

    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="kitafenster-screenshots-", ignore_cleanup_errors=True
    ) as profile:
        process = subprocess.Popen(
            [
                str(EDGE),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--remote-allow-origins=*",
                f"--remote-debugging-port={PORT}",
                f"--user-data-dir={profile}",
                "--window-size=1440,900",
                BASE_URL,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        devtools = None
        try:
            page = wait_for_page(PORT)
            devtools = DevTools(page["webSocketDebuggerUrl"])
            devtools.call("Page.enable")
            devtools.call("Runtime.enable")
            devtools.call("Page.navigate", {"url": BASE_URL})
            devtools.call(
                "Emulation.setDeviceMetricsOverride",
                {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False},
            )
            wait_ready(
                devtools, "location.origin === 'http://127.0.0.1:8088' && document.readyState === 'complete'"
            )
            login = json.dumps(
                {"username": "admin", "password": os.getenv("ADMIN_PASSWORD", "KitaLokal2026!")}
            )
            devtools.evaluate(
                f"fetch({json.dumps(BASE_URL + '/api/login')},{{method:'POST',headers:{{'Content-Type':'application/json'}},"
                f"body:{json.dumps(login)}}}).then(r=>{{if(!r.ok)throw new Error('Anmeldung fehlgeschlagen');return r.json()}})"
            )
            devtools.call("Page.reload", {"ignoreCache": True})
            wait_ready(
                devtools,
                "!document.querySelector('#app').hidden && document.querySelectorAll('.device-card').length > 0",
            )

            shots = [
                ("01-uebersicht.png", "overview", None),
                ("02-bilderrahmen.png", "devices", None),
                (
                    "03-bildschirmvorschau.png",
                    "devices",
                    "document.querySelector('[data-action=preview]').click()",
                ),
                ("04-inhalte.png", "content", None),
                (
                    "05-meldung-vorschau.png",
                    "content",
                    "document.querySelector('.notice-card [data-action=notice]').click();"
                    "setTimeout(()=>document.querySelector('#dialog .notice-preview')?.scrollIntoView({block:'center'}),250)",
                ),
                ("06-gruppen-nas.png", "groups", None),
                ("07-betriebszeiten.png", "operating", None),
                (
                    "08-geteilte-anzeige.png",
                    "devices",
                    "document.querySelector('.table-wrap [data-action=device]').click();"
                    "setTimeout(()=>{const box=document.querySelector('[name=split_enabled]');"
                    "if(box&&!box.checked)box.click();"
                    "document.querySelector('#split-settings')?.scrollIntoView({block:'center'})},250)",
                ),
            ]
            for filename, page_name, action in shots:
                devtools.evaluate(
                    "document.querySelector('#dialog').open && document.querySelector('#dialog').close();"
                    f"navigate({json.dumps(page_name)});window.scrollTo(0,0)"
                )
                time.sleep(0.35)
                if action:
                    devtools.evaluate(action)
                    time.sleep(0.8)
                devtools.screenshot(OUTPUT / filename)
                print(filename)
        finally:
            if devtools is not None:
                try:
                    devtools.call("Browser.close")
                except (ConnectionError, OSError):
                    pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)


if __name__ == "__main__":
    main()
