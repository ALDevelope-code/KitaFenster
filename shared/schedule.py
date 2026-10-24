"""Dieselbe Prioritätslogik läuft auf dem Server und offline auf dem Pi."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

MODES = {
    "photos": "Fotos",
    "plan": "Dokument",
    "messages": "Meldungen",
    "mixed": "Gemischt",
    "black": "Ruhezeit",
}


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def active_period(item, now):
    start, end = parse_time(item.get("starts_at")), parse_time(item.get("ends_at"))
    return (start is None or now >= start) and (end is None or now < end)


def in_window(days, start, end, local):
    """Halboffenes Intervall; bei Mitternachtswechsel gehört es zum Starttag."""
    minute = local.strftime("%H:%M")
    day = local.weekday()
    if start == end:
        return day in days  # ausdrücklich: ganztägig
    if start < end:
        return day in days and start <= minute < end
    return (day in days and minute >= start) or ((day - 1) % 7 in days and minute < end)


def matches(target, device):
    return (
        target["kind"] == "all"
        or (target["kind"] == "group" and target["id"] == device["group_id"])
        or (target["kind"] == "device" and target["id"] == device["id"])
    )


def document_references(settings):
    """Include paused selections too, so they survive offline use and cannot be deleted."""
    entries = [settings, *settings.get("content_windows", []), *settings.get("playlist", [])]
    secondary = settings.get("split", {}).get("secondary", {})
    entries.extend([secondary, *secondary.get("playlist", [])])
    return {entry["document_id"] for entry in entries if entry.get("document_id")}


def resolve(manifest, now=None):
    now = now or datetime.now(timezone.utc)
    settings = manifest["settings"]
    local = now.astimezone(ZoneInfo(settings.get("timezone", "Europe/Berlin")))
    notices = [n for n in manifest.get("notices", []) if active_period(n, now)]
    urgent = sorted([n for n in notices if n.get("urgent")], key=lambda n: n["id"])
    if urgent:
        return {"mode": "messages", "reason": "Sofortmeldung", "notices": urgent}
    operating = manifest["operating_hours"]
    operating_local = now.astimezone(ZoneInfo(operating["timezone"]))
    if operating["enabled"] and not any(
        in_window(w["days"], w["start"], w["end"], operating_local) for w in operating["windows"]
    ):
        return {"mode": "black", "reason": "Außerhalb der Betriebszeiten", "notices": []}
    result = resolve_area(manifest, now, local, notices, "main")
    if settings.get("split", {}).get("enabled"):
        result["secondary"] = resolve_area(manifest, now, local, notices, "secondary")
    return result


def content_settings(settings, area="main"):
    if area == "secondary":
        return {**settings, **settings.get("split", {}).get("secondary", {"default_mode": "messages"})}
    return settings


def resolve_area(manifest, now, local, notices, area):
    settings = content_settings(manifest["settings"], area)
    timed = settings.get("content_windows_enabled", True)
    window = next(
        (
            (i, h)
            for i, h in enumerate(settings.get("content_windows", []))
            if timed and h.get("area", "main") == area and in_window(h["days"], h["start"], h["end"], local)
        ),
        None,
    )
    manual = manifest.get("manual" if area == "main" else "manual_secondary")
    if manual and (not manual.get("until") or now < parse_time(manual["until"])):
        return {
            "mode": manual["mode"],
            "reason": "Manuell gewählt",
            "notices": notices,
            "document_id": settings.get("document_id"),
            "area": area,
        }
    if window and window[1].get("mode"):
        index, selected = window
        return {
            "mode": selected["mode"],
            "reason": "Inhaltszeitfenster "
            + str(index + 1)
            + (": " + selected["name"] if selected.get("name") else ""),
            "notices": notices,
            "document_id": selected.get("document_id"),
            "area": area,
        }
    return {
        "mode": settings["default_mode"],
        "reason": "Standardanzeige",
        "notices": notices,
        "document_id": settings.get("document_id"),
        "area": area,
    }


def slides(manifest, decision):
    settings = content_settings(manifest["settings"], decision.get("area", "main"))

    def content(mode, seconds, document_id=None):
        if mode == "photos":
            return [
                {"kind": "image", "asset": a, "seconds": seconds, "fit": settings["fit"]}
                for a in manifest.get("photos", [])
            ]
        if mode == "plan":
            assets = (
                manifest.get("documents", {}).get(document_id, {}).get("assets", [])
                if document_id
                else manifest.get("plan", [])
            )
            return [{"kind": "image", "asset": a, "seconds": seconds, "fit": "contain"} for a in assets]
        if mode == "messages":
            return [{"kind": "notice", "notice": n, "seconds": seconds} for n in decision["notices"]]
        return []

    if decision["mode"] == "mixed":
        result = []
        for entry in settings["playlist"]:
            result.extend(content(entry["mode"], entry["seconds"], entry.get("document_id")))
        return result
    return content(decision["mode"], settings["interval"], decision.get("document_id"))
