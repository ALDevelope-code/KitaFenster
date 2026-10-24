import ctypes as ct
from types import SimpleNamespace

import pytest

from player.display_power import DisplayPower, KmsPower, ObjectProperties, PropertyHeader, find_connector
from player.motion import MotionGate


class Sensor:
    high = False
    broken = False
    closed = False

    def active(self):
        if self.broken:
            raise OSError("GPIO access lost")
        return self.high

    def close(self):
        self.closed = True


def settings(**changes):
    return {"enabled": True, "idle_minutes": 1, "power_mode": "hdmi", **changes}


def test_disabled_and_old_settings_never_open_gpio():
    calls = []

    def forbidden():
        calls.append(1)
        raise AssertionError("Must not open GPIO")

    gate = MotionGate(forbidden)
    for config in ({}, {"enabled": False}):
        assert not gate.update(config, 1000).idle
        assert gate.sensor is None
    assert calls == []


def test_warmup_motion_hold_and_urgent_override_use_monotonic_time():
    sensor = Sensor()
    gate = MotionGate(lambda: sensor)
    assert not gate.update(settings(), 0).idle
    assert "läuft ein" in gate.update(settings(), 59).reason
    assert not gate.update(settings(), 60).idle
    assert gate.update(settings(), 120).idle
    sensor.high = True
    assert not gate.update(settings(), 121).idle
    assert not gate.update(settings(), 600).idle  # sustained HIGH extends activity
    sensor.high = False
    assert not gate.update(settings(), 659).idle
    assert gate.update(settings(), 660).idle
    assert not gate.update(settings(), 661, urgent=True).idle
    assert not gate.update(settings(), 720).idle
    assert gate.update(settings(), 721).idle


def test_timeout_change_and_disable_take_effect_while_asleep():
    sensor = Sensor()
    gate = MotionGate(lambda: sensor)
    gate.update(settings(), 0)
    assert gate.update(settings(), 120).idle
    assert not gate.update(settings(idle_minutes=5), 121).idle
    assert not gate.update(settings(enabled=False), 122).idle
    assert sensor.closed
    assert gate.sensor is None
    assert "läuft ein" in gate.update(settings(), 123).reason


def test_gpio_errors_fail_open_and_retry_without_busy_loop():
    calls, sensor = [], Sensor()

    def factory():
        calls.append(1)
        if len(calls) == 1:
            raise OSError("Permission denied")
        return sensor

    gate = MotionGate(factory)
    result = gate.update(settings(), 0)
    assert not result.idle and "nicht lesbar" in result.error
    assert gate.update(settings(), 29).error
    assert len(calls) == 1
    assert not gate.update(settings(), 30).error
    sensor.broken = True
    result = gate.update(settings(), 1000)
    assert not result.idle and result.error
    assert sensor.closed


def test_live_signal_history_separates_sensor_hold_from_software_timeout():
    sensor = Sensor()
    gate = MotionGate(lambda: sensor)
    initial = gate.update(settings(), 100).diagnostics
    assert initial["signal"] is False
    assert initial["warmup_seconds"] == 60
    assert initial["remaining_seconds"] == 60  # Warmup is not part of the software timeout.
    assert initial["events"][0]["initial"] is True
    gate.update(settings(), 160)
    sensor.high = True
    gate.update(settings(), 170)
    high = gate.update(settings(), 190).diagnostics
    assert high["phase"] == "high"
    assert high["signal_seconds"] == 20
    assert high["remaining_seconds"] == 60
    sensor.high = False
    low = gate.update(settings(), 191).diagnostics
    assert low["events"][0]["previous_seconds"] == 21
    assert low["events"][0]["signal"] is False
    assert not low["events"][0]["initial"]
    holding = gate.update(settings(), 220).diagnostics
    assert holding["phase"] == "hold"
    assert holding["remaining_seconds"] == 30
    assert gate.update(settings(), 250).diagnostics["phase"] == "idle"
    urgent = gate.update(settings(), 251, urgent=True).diagnostics
    assert urgent["phase"] == "urgent" and urgent["signal"] is False
    assert urgent["remaining_seconds"] == 60


def test_live_history_is_bounded_and_errors_never_look_like_low():
    sensor = Sensor()
    gate = MotionGate(lambda: sensor)
    for now in range(80):
        sensor.high = not sensor.high
        report = gate.update(settings(), now)
    assert len(report.diagnostics["events"]) == 20
    sensor.broken = True
    report = gate.update(settings(), 81)
    assert report.diagnostics["signal"] is None
    assert report.diagnostics["signal_seconds"] is None
    assert report.diagnostics["phase"] == "error"
    assert report.diagnostics["retry_seconds"] == 30
    assert "GPIO access lost" in report.diagnostics["sensor_error"]
    sensor.broken = False
    retry = gate.update(settings(), 111).diagnostics
    assert retry["events"][0]["initial"] is True  # Access gap is not a measured signal phase.
    disabled = gate.update(settings(enabled=False), 112).diagnostics
    assert disabled["phase"] == "disabled"
    assert disabled["signal"] is None and disabled["events"] == []


class PowerBackend:
    def __init__(self):
        self.calls = []
        self.fail_sleep = False
        self.fail_wake = False

    def set_awake(self, awake):
        self.calls.append(awake)
        if (awake and self.fail_wake) or (not awake and self.fail_sleep):
            raise OSError("Modeset failed")

    def close(self):
        self.calls.append("closed")


def test_power_switches_once_and_restores_when_disabled_or_black_selected():
    backend = PowerBackend()
    calls = []

    def factory():
        calls.append(1)
        return backend

    power = DisplayPower(factory)
    assert power.apply(False, "hdmi") == "on"
    assert power.apply(True, "black") == "black"
    assert not calls
    assert power.apply(True, "hdmi") == "standby"
    assert power.apply(True, "hdmi") == "standby"
    assert backend.calls == [False]
    assert power.apply(True, "black") == "black"
    assert backend.calls == [False, True]
    power.apply(True, "hdmi")
    assert power.apply(False, "hdmi") == "on"
    assert backend.calls == [False, True, False, True]
    power.close()
    assert backend.calls[-1] == "closed"


def test_failed_sleep_uses_black_and_does_not_repeat_ioctl_every_frame():
    backend = PowerBackend()
    backend.fail_sleep = True
    power = DisplayPower(lambda: backend)
    assert power.apply(True, "hdmi") == "black"
    assert power.error
    power.apply(True, "hdmi")
    assert backend.calls == [False]
    assert power.apply(False, "hdmi") == "on"
    assert not power.error
    backend.fail_sleep = False
    assert power.apply(True, "hdmi") == "standby"
    backend.fail_wake = True
    with pytest.raises(OSError):
        power.apply(False, "hdmi")
    assert power.asleep  # caller must not flip; supervisor restarts display


def test_connector_selection_uses_existing_master_and_ignores_other_cards(tmp_path, monkeypatch):
    fd_root, sys_root = tmp_path / "fd", tmp_path / "drm"
    fd_root.mkdir()
    sys_root.mkdir()
    mapping = {"3": "/dev/dri/card0", "4": "/dev/dri/card1", "5": "/dev/dri/card1"}
    for fd in mapping:
        (fd_root / fd).touch()
    for card, connector_id in [("card0", 10), ("card1", 20)]:
        connector = sys_root / (card + "-HDMI-A-1")
        connector.mkdir()
        (connector / "enabled").write_text("enabled\n")
        (connector / "status").write_text("connected\n")
        (connector / "connector_id").write_text(str(connector_id))
    monkeypatch.setattr("player.display_power.os.readlink", lambda p: mapping[p.name])
    drm = SimpleNamespace(drmIsMaster=lambda fd: int(fd in (4, 5)))
    fd, connector = find_connector(drm, fd_root=fd_root, sys_root=sys_root)
    assert fd in (4, 5) and connector == 20
    (sys_root / "card1-HDMI-A-1/status").write_text("disconnected\n")
    with pytest.raises(OSError):
        find_connector(drm, fd_root=fd_root, sys_root=sys_root)


def test_dpms_property_is_freed_and_only_owned_duplicate_is_closed(monkeypatch):
    prop = PropertyHeader(42, 0, b"DPMS")
    ids = (ct.c_uint32 * 1)(42)
    values = (ct.c_uint64 * 1)(0)
    props = ObjectProperties(1, ids, values)
    freed, switches, closed = [], [], []
    drm = SimpleNamespace(
        drmModeObjectGetProperties=lambda *args: ct.pointer(props),
        drmModeGetProperty=lambda *args: ct.pointer(prop),
        drmModeFreeProperty=lambda ptr: freed.append("property"),
        drmModeFreeObjectProperties=lambda ptr: freed.append("objects"),
        drmModeConnectorSetProperty=lambda *args: switches.append(args) or 0,
    )
    import pygame

    monkeypatch.setattr(pygame.display, "get_driver", lambda: "KMSDRM")
    monkeypatch.setattr("player.display_power.load_drm", lambda: drm)
    monkeypatch.setattr("player.display_power.find_connector", lambda lib: (7, 24))
    monkeypatch.setattr("player.display_power.os.dup", lambda fd: 8)
    monkeypatch.setattr("player.display_power.os.close", closed.append)
    power = KmsPower()
    assert freed == ["property", "objects"]
    power.set_awake(False)
    power.close()
    assert switches == [(8, 24, 42, 3), (8, 24, 42, 0)]
    assert closed == [8]  # Never close SDL's descriptor 7.
