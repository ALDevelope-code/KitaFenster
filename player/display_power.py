"""Switch the active SDL KMS connector using the player's existing DRM master.

No new DRM master, root helper, X11 server or shell command is involved.
The render loop must stop page flips while HDMI is disabled.
"""

import ctypes as ct
import os
import re
from pathlib import Path

DRM_MODE_OBJECT_CONNECTOR = 0xC0C0C0C0


class ObjectProperties(ct.Structure):
    _fields_ = [
        ("count_props", ct.c_uint32),
        ("props", ct.POINTER(ct.c_uint32)),
        ("prop_values", ct.POINTER(ct.c_uint64)),
    ]


class PropertyHeader(ct.Structure):
    # Only the fixed prefix is accessed. libdrm owns/frees the full structure.
    _fields_ = [("prop_id", ct.c_uint32), ("flags", ct.c_uint32), ("name", ct.c_char * 32)]


def load_drm():
    drm = ct.CDLL("libdrm.so.2", use_errno=True)
    declarations = {
        "drmIsMaster": ([ct.c_int], ct.c_int),
        "drmModeObjectGetProperties": ([ct.c_int, ct.c_uint32, ct.c_uint32], ct.POINTER(ObjectProperties)),
        "drmModeFreeObjectProperties": ([ct.POINTER(ObjectProperties)], None),
        "drmModeGetProperty": ([ct.c_int, ct.c_uint32], ct.POINTER(PropertyHeader)),
        "drmModeFreeProperty": ([ct.POINTER(PropertyHeader)], None),
        "drmModeConnectorSetProperty": ([ct.c_int, ct.c_uint32, ct.c_uint32, ct.c_uint64], ct.c_int),
    }
    for name, (arguments, result) in declarations.items():
        function = getattr(drm, name)
        function.argtypes, function.restype = arguments, result
    return drm


def find_connector(drm, *, fd_root=Path("/proc/self/fd"), sys_root=Path("/sys/class/drm")):
    candidates = {}
    for entry in fd_root.iterdir():
        try:
            target = os.readlink(entry)
            if not re.fullmatch(r"/dev/dri/card[0-9]+", target):
                continue
            fd = int(entry.name)
            if drm.drmIsMaster(fd) != 1:
                continue
            for connector in sys_root.glob(Path(target).name + "-HDMI-A-*"):
                if (connector / "enabled").read_text().strip() == "enabled" and (
                    connector / "status"
                ).read_text().strip() == "connected":
                    connector_id = int((connector / "connector_id").read_text())
                    candidates.setdefault((target, connector_id), (fd, connector_id))
        except (OSError, ValueError):
            continue
    if len(candidates) != 1:
        raise OSError("Kein eindeutiger aktiver HDMI-Anschluss des Players gefunden")
    return next(iter(candidates.values()))


class KmsPower:
    def __init__(self):
        import pygame

        if pygame.display.get_driver().upper() != "KMSDRM":
            raise OSError("HDMI-Abschaltung benötigt den KMS/DRM-Player")
        self.drm = load_drm()
        fd, self.connector = find_connector(self.drm)
        self.fd = os.dup(fd)  # Same open file description; close only our duplicate.
        self.off = False
        try:
            self.property = self._dpms_property()
        except Exception:
            os.close(self.fd)
            raise

    def _dpms_property(self):
        properties = self.drm.drmModeObjectGetProperties(self.fd, self.connector, DRM_MODE_OBJECT_CONNECTOR)
        if not properties:
            raise OSError("HDMI-Eigenschaften nicht lesbar")
        try:
            for i in range(properties.contents.count_props):
                prop = self.drm.drmModeGetProperty(self.fd, properties.contents.props[i])
                if not prop:
                    continue
                try:
                    if prop.contents.name == b"DPMS":
                        return prop.contents.prop_id
                finally:
                    self.drm.drmModeFreeProperty(prop)
        finally:
            self.drm.drmModeFreeObjectProperties(properties)
        raise OSError("HDMI-Anschluss unterstützt keine DPMS-Abschaltung")

    def set_awake(self, awake):
        # DPMS is a legacy property mapped to CRTC ACTIVE on atomic drivers.
        result = self.drm.drmModeConnectorSetProperty(
            self.fd, self.connector, self.property, 0 if awake else 3
        )
        if result != 0:
            raise OSError(ct.get_errno(), "HDMI-Schaltung fehlgeschlagen")
        self.off = not awake

    def close(self):
        try:
            if self.off:
                self.set_awake(True)
        finally:
            os.close(self.fd)


class DisplayPower:
    def __init__(self, backend_factory=KmsPower):
        self.backend_factory = backend_factory
        self.backend = None
        self.asleep = False
        self.error = ""

    def apply(self, sleeping, method):
        if not sleeping or method != "hdmi":
            if self.asleep:
                # Do not resume page flips on a disabled CRTC after a failed wake.
                # The supervisor will restart the player if restoring HDMI fails.
                self.backend.set_awake(True)
                self.asleep = False
            self.error = ""
            return "black" if sleeping else "on"
        if self.asleep:
            return "standby"
        if self.error:
            return "black"
        try:
            if self.backend is None:
                self.backend = self.backend_factory()
            self.backend.set_awake(False)
            self.asleep = True
            return "standby"
        except Exception as error:
            detail = " ".join(str(error).split())[:160] or type(error).__name__
            self.error = (
                "HDMI-Abschaltung nicht verfügbar; zeige Schwarzbild. Monitor und KMS/DRM prüfen. " + detail
            )
            return "black"

    def close(self):
        if self.backend is not None:
            try:
                self.backend.close()
            except Exception:
                pass
            self.backend = None
