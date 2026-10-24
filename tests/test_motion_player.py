import threading
from types import SimpleNamespace

import pygame
import pytest
from conftest import image_bytes
from test_player import manifest

import player.__main__ as application
from player.cache import Cache, atomic_json
from player.motion import MotionState


@pytest.mark.parametrize("sleep_output", ["standby", "black"])
def test_player_does_not_flip_while_hdmi_off_and_redraws_after_wake(tmp_path, monkeypatch, sleep_output):
    data = image_bytes()
    content = manifest(data)
    content["settings"].update(transition="none", motion={"enabled": True, "idle_minutes": 1})
    cache = Cache(tmp_path / "cache")
    cache.install(content, lambda *args: data)
    updated_data = image_bytes("blue")
    updated = manifest(updated_data, "2")
    updated["settings"] = content["settings"]
    snapshots = 0

    def snapshot():
        nonlocal snapshots
        snapshots += 1
        if snapshots == 3:
            # A successful sync publishes new media while the screen is asleep.
            cache.install(updated, lambda *args: updated_data)
        return updated if snapshots >= 3 else content

    config = tmp_path / "player.json"
    atomic_json(config, {"cache_dir": str(cache.root)})
    reports, flips, switches = [], [], []
    worker = SimpleNamespace(
        cache=cache,
        stop=threading.Event(),
        restart=threading.Event(),
        start=lambda: None,
        snapshot=snapshot,
        report=lambda *args: reports.append(args),
    )
    phases = iter([False, True, True, False])
    closed = []
    gate = SimpleNamespace(
        update=lambda *args, **kwargs: MotionState(idle=next(phases), reason="PIR"),
        close=lambda: closed.append("gpio"),
    )

    def power(sleeping, method):
        switches.append(sleeping)
        return sleep_output if sleeping else "on"

    display = SimpleNamespace(apply=power, error="", close=lambda: closed.append("power"))
    monkeypatch.setattr(application, "SyncWorker", lambda cfg: worker)
    monkeypatch.setattr(application, "MotionGate", lambda: gate)
    monkeypatch.setattr(application, "DisplayPower", lambda: display)
    monkeypatch.setattr(pygame.time, "Clock", lambda: SimpleNamespace(tick=lambda fps: None))

    def flip():
        if sleep_output == "standby":
            assert not switches[-1]
        surface = pygame.display.get_surface()
        flips.append(surface.get_at((surface.get_width() // 2, surface.get_height() // 2))[:3])

    monkeypatch.setattr(pygame.display, "flip", flip)
    monkeypatch.setattr("sys.argv", ["player", "--config", str(config), "--windowed", "--frames", "4"])
    application.main()
    assert switches == [False, True, True, False]
    assert [report[0] for report in reports] == ["photos", "sleep", "sleep", "photos"]
    assert len(flips) == (2 if sleep_output == "standby" else 3)
    assert flips[0][0] > 200 and flips[0][2] < 10
    assert flips[-1][2] > 200 and flips[-1][0] < 10  # Fresh blue image after wake.
    if sleep_output == "black":
        assert flips[1] == (0, 0, 0)
    assert closed == ["gpio", "power"]
    assert worker.stop.is_set()


@pytest.mark.parametrize("sensor_enabled", [True, False])
def test_opening_hours_and_urgent_messages_override_presence(tmp_path, monkeypatch, sensor_enabled):
    content = manifest(image_bytes())
    content["settings"].update(transition="none", motion={"enabled": sensor_enabled})
    config = tmp_path / "player.json"
    atomic_json(config, {})
    worker = SimpleNamespace(
        cache=Cache(tmp_path / "cache"),
        stop=threading.Event(),
        restart=threading.Event(),
        start=lambda: None,
        snapshot=lambda: content,
        report=lambda *args: None,
    )
    decisions = iter(
        [
            {"mode": "black", "reason": "Außerhalb der Betriebszeiten", "notices": []},
            {"mode": "messages", "reason": "Sofortmeldung", "notices": []},
        ]
    )
    sensed = iter([MotionState(idle=False), MotionState(idle=True)])
    switches = []
    gate = SimpleNamespace(update=lambda *args, **kwargs: next(sensed), close=lambda: None)

    def power(sleeping, method):
        switches.append(sleeping)
        return "standby" if sleeping else "on"

    monkeypatch.setattr(application, "resolve", lambda m: next(decisions))
    monkeypatch.setattr(application, "SyncWorker", lambda cfg: worker)
    monkeypatch.setattr(application, "MotionGate", lambda: gate)
    monkeypatch.setattr(
        application, "DisplayPower", lambda: SimpleNamespace(apply=power, error="", close=lambda: None)
    )
    monkeypatch.setattr(pygame.time, "Clock", lambda: SimpleNamespace(tick=lambda fps: None))
    monkeypatch.setattr("sys.argv", ["player", "--config", str(config), "--windowed", "--frames", "2"])
    application.main()
    assert switches == [True, False]
