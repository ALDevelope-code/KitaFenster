from datetime import datetime, timezone

from server.models import OperatingHours, Settings
from shared.schedule import in_window, resolve, slides


def at(value):
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def base():
    return {
        "settings": Settings().model_dump(),
        "photos": ["photo"],
        "plan": ["p1", "p2"],
        "notices": [],
        "operating_hours": OperatingHours().model_dump(),
        "manual": None,
    }


def test_priority_and_offline_expiration():
    m = base()
    m["operating_hours"] = {
        "enabled": True,
        "timezone": "Europe/Berlin",
        "windows": [{"days": [0], "start": "07:00", "end": "18:00"}],
    }
    m["settings"]["content_windows"] = [{"days": [0], "start": "07:00", "end": "12:00", "mode": "plan"}]
    now = at("2026-09-14T08:00:00")
    assert resolve(m, now)["mode"] == "plan"
    m["manual"] = {"mode": "mixed", "until": "2026-09-14T09:00:00+00:00"}
    assert resolve(m, now)["mode"] == "mixed"
    m["notices"] = [
        {
            "id": "n",
            "urgent": True,
            "starts_at": "2026-09-14T07:00:00+00:00",
            "ends_at": "2026-09-14T08:30:00+00:00",
        }
    ]
    assert resolve(m, now)["reason"] == "Sofortmeldung"
    assert resolve(m, at("2026-09-14T08:30:00"))["mode"] == "mixed"
    assert resolve(m, at("2026-09-14T09:00:00"))["mode"] == "plan"
    assert resolve(m, at("2026-09-14T13:00:00"))["mode"] == "photos"
    assert resolve(m, at("2026-09-14T18:00:00"))["mode"] == "black"
    m["notices"][0]["ends_at"] = None
    assert resolve(m, at("2026-09-14T18:00:00"))["mode"] == "messages"


def test_overnight_and_end_exclusive():
    assert in_window([0], "22:00", "02:00", at("2026-09-14T23:00:00"))
    assert in_window([0], "22:00", "02:00", at("2026-09-15T01:00:00"))
    assert not in_window([0], "22:00", "02:00", at("2026-09-15T02:00:00"))
    assert not in_window([0], "22:00", "02:00", at("2026-09-15T23:00:00"))


def test_timezone_dst_and_window_priority_are_deterministic():
    m = base()
    m["settings"]["content_windows"] = [
        {"id": id, "name": id, "days": [6], "start": "02:00", "end": "03:00", "mode": mode, "priority": 5}
        for id, mode in [("a", "messages"), ("z", "plan")]
    ]
    # The repeated local 02:30 during DST fall-back produces the same decision.
    assert resolve(m, at("2026-10-25T00:30:00"))["mode"] == "messages"
    assert resolve(m, at("2026-10-25T01:30:00"))["mode"] == "messages"
    assert resolve(m, at("2026-10-25T02:30:00"))["mode"] == "photos"


def test_mixed_playlist_order_and_durations():
    m = base()
    m["settings"]["default_mode"] = "mixed"
    m["settings"]["playlist"] = [{"mode": "plan", "seconds": 25}, {"mode": "photos", "seconds": 9}]
    result = slides(m, resolve(m))
    assert [s["asset"] for s in result] == ["p1", "p2", "photo"]
    assert [s["seconds"] for s in result] == [25, 25, 9]
    assert all(s["fit"] == "contain" for s in result)
