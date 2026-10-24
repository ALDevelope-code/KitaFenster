"""Optional local PIR gate; no GPIO access while disabled."""

import math
from collections import deque
from dataclasses import dataclass, field

PIR_GPIO = 17  # BCM numbering: physical header pin 11.
WARMUP_SECONDS = 60
RETRY_SECONDS = 30


class PirInput:
    def __init__(self):
        from gpiozero import DigitalInputDevice
        from gpiozero.pins.lgpio import LGPIOFactory

        self.factory = LGPIOFactory()
        try:
            self.input = DigitalInputDevice(PIR_GPIO, pull_up=False, pin_factory=self.factory)
        except Exception:
            self.factory.close()
            raise

    def active(self):
        return bool(self.input.value)

    def close(self):
        try:
            self.input.close()
        finally:
            self.factory.close()


@dataclass(frozen=True)
class MotionState:
    idle: bool = False
    reason: str = ""
    error: str = ""
    diagnostics: dict = field(default_factory=dict)


class MotionGate:
    def __init__(self, sensor_factory=PirInput):
        self.sensor_factory = sensor_factory
        self.sensor = None
        self.enabled = False
        self.last_active = 0.0
        self.warm_until = 0.0
        self.retry_at = 0.0
        self.error = ""
        self.signal = None
        self.signal_since = None
        self.events = deque(maxlen=20)

    def update(self, settings, now, *, urgent=False):
        enabled = bool(settings.get("enabled", False))
        if not enabled:
            self.close()
            self.enabled = False
            self.error = ""
            self.retry_at = 0
            self.signal = self.signal_since = None
            self.events.clear()
            return self._state(settings, now, "disabled")
        if not self.enabled:
            self.enabled = True
            self.last_active = now
        if self.sensor is None and now >= self.retry_at:
            try:
                self.sensor = self.sensor_factory()
                self.warm_until = now + WARMUP_SECONDS
                self.error = ""
            except Exception as error:
                self._failed(now, error)
        if self.sensor is not None:
            try:
                active = self.sensor.active()
                if active != self.signal:
                    self.events.append(
                        {
                            "at": now,
                            "signal": active,
                            "initial": self.signal is None,
                            "previous_seconds": (
                                round(now - self.signal_since, 1) if self.signal_since is not None else None
                            ),
                        }
                    )
                    self.signal, self.signal_since = active, now
                if active or urgent or now < self.warm_until:
                    self.last_active = now
                if now < self.warm_until:
                    self.last_active = self.warm_until
                    return self._state(
                        settings, now, "warmup", reason="Bewegungssensor läuft ein (60 Sekunden)"
                    )
                if urgent:
                    return self._state(settings, now, "urgent")
                if now - self.last_active >= settings.get("idle_minutes", 5) * 60:
                    return self._state(settings, now, "idle", idle=True, reason="Keine Bewegung erkannt")
                return self._state(
                    settings,
                    now,
                    "high" if active else "hold",
                    reason="Bewegung erkannt" if active else "Nachlaufzeit läuft",
                )
            except Exception as error:
                self._failed(now, error)
        # A detectable hardware/permission error must not hide content.
        return self._state(settings, now, "error", error=self.error)

    def _state(self, settings, now, phase, **state):
        readable = self.sensor is not None
        return MotionState(
            **state,
            diagnostics={
                "enabled": self.enabled,
                "phase": phase,
                "signal": self.signal if readable else None,
                "signal_seconds": round(now - self.signal_since, 1)
                if readable and self.signal_since is not None
                else None,
                "warmup_seconds": max(0, math.ceil(self.warm_until - now)) if readable else 0,
                "remaining_seconds": max(
                    0, math.ceil(settings.get("idle_minutes", 5) * 60 - max(0, now - self.last_active))
                )
                if readable
                else None,
                "idle_minutes": settings.get("idle_minutes", 5),
                "power_mode": settings.get("power_mode", "hdmi"),
                "retry_seconds": max(0, math.ceil(self.retry_at - now)) if self.error else 0,
                "sensor_error": self.error,
                "events": [
                    {
                        "signal": event["signal"],
                        "initial": event["initial"],
                        "ago_seconds": round(now - event["at"], 1),
                        "previous_seconds": event["previous_seconds"],
                    }
                    for event in reversed(self.events)
                ],
            },
        )

    def _failed(self, now, error):
        self.close()
        self.signal = self.signal_since = None
        self.retry_at = now + RETRY_SECONDS
        detail = " ".join(str(error).split())[:160] or type(error).__name__
        self.error = (
            "Bewegungssensor nicht lesbar; GPIO17, Anschluss und gpio-Rechte prüfen. Anzeige bleibt aktiv. "
            + detail
        )

    def close(self):
        if self.sensor is not None:
            try:
                self.sensor.close()
            except Exception:
                pass
            self.sensor = None


def main():
    import argparse
    import time

    parser = argparse.ArgumentParser(description="HC-SR501 an GPIO17 (Pin 11) für 120 Sekunden prüfen")
    parser.parse_args()
    print("Sensorfunktion auf der Webseite vorher ausschalten (GPIO darf nur einmal belegt sein).")
    sensor = None
    try:
        sensor = PirInput()
        started, previous = time.monotonic(), None
        while time.monotonic() - started < 120:
            active = sensor.active()
            if active != previous:
                elapsed = int(time.monotonic() - started)
                print(f"{elapsed:3d}s GPIO17: {'HIGH / Bewegung' if active else 'LOW / Ruhe'}", flush=True)
                previous = active
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    except Exception as error:
        print(f"Sensorprüfung fehlgeschlagen: {error}")
        return 1
    finally:
        if sensor is not None:
            sensor.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
