import hashlib
import json

from server.documents import list_assignment
from server.models import OperatingHours
from shared.schedule import document_references, matches, resolve


def document_allowed(document, device, group):
    return (
        device["allow_internal"]
        or document.get("public", False)
        or group["id"] in document.get("parent_groups", [])
        or (
            not group.get("plan_path")
            and group.get("plan_id") == document["id"]
            and group.get("plan_public", False)
        )
    )


def manifest_for(db, device, descriptors=True):
    group = db.get("group", device["group_id"])
    snapshot = db.get("snapshot", device["group_id"]) or {}
    source_matches = snapshot.get("folder") == group["folder"]
    notices = [
        n
        for n in db.all("notice")
        if matches(n["target"], device) and (not n["internal"] or device["allow_internal"])
    ]
    plan = []
    if group.get("plan_path") and not group.get("document_list_migrated"):
        if (
            source_matches
            and snapshot.get("plan_path") == group["plan_path"]
            and (
                device["allow_internal"]
                or (group.get("plan_public", False) and snapshot.get("plan_public", False))
            )
        ):
            plan = list(snapshot.get("plan", []))
    elif group.get("plan_id") and not group.get("plan_path"):
        document = db.get("document", group["plan_id"])
        if document and document_allowed(document, device, group):
            plan = list(document["assets"])
    photos = snapshot.get("photos", []) if source_matches else []
    asset_ids = photos + plan
    documents = {}
    common_documents = []
    groups = db.all("group")
    for document in sorted(db.all("document"), key=lambda d: (d["name"].casefold(), d["id"])):
        if document["kind"] != "plan" or not document_allowed(document, device, group):
            continue
        if document.get("legacy_nas_group"):
            source = next((g for g in groups if g["id"] == document["legacy_nas_group"]), {})
            if source.get("folder") != document.get("legacy_nas_folder") or source.get(
                "plan_path"
            ) != document.get("legacy_nas_path"):
                continue
        assignment = list_assignment(document, groups)
        if assignment.get("all_groups") or group["id"] in assignment.get("group_ids", []):
            common_documents.append(document["id"])
            if not (group.get("plan_id") == document["id"] and not group.get("plan_path")):
                plan.extend(document["assets"])
            asset_ids.extend(document["assets"])
    for id in sorted(document_references(device["settings"])):
        document = db.get("document", id)
        if document and document["kind"] == "plan" and document_allowed(document, device, group):
            documents[id] = {key: document[key] for key in ("name", "assets")}
            asset_ids.extend(document["assets"])
    for notice in notices:
        document = db.get("document", notice["image_id"]) if notice.get("image_id") else None
        notice["image"] = document["assets"][0] if document and document["assets"] else None
        if notice["image"]:
            asset_ids.append(notice["image"])
    # Do not mutate snapshot photos while collecting other assets.
    result = {
        "version": 1,
        "device_id": device["id"],
        "group_id": device["group_id"],
        "policy": {
            "group_id": device["group_id"],
            "allow_internal": device["allow_internal"],
            "plan_public": group.get("plan_public", False),
            "folder": group["folder"],
            "plan_path": group.get("plan_path", ""),
            "plan_id": group.get("plan_id"),
            "plan_access": bool(plan),
            "documents": sorted(documents),
            "common_documents": common_documents,
        },
        "group_name": group["name"],
        "settings": device["settings"],
        "manual": device.get("manual"),
        "manual_secondary": device.get("manual_secondary"),
        "photos": photos,
        "plan": plan,
        "documents": documents,
        "notices": notices,
        "operating_hours": device["settings"].get("operating_hours_override")
        or {
            k: v
            for k, v in (db.get("operating_hours", "global") or OperatingHours().model_dump()).items()
            if k != "id"
        },
        "assets": db.get_many("asset", asset_ids) if descriptors else dict.fromkeys(asset_ids),
    }
    result["revision"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    return result


def device_status(db, device):
    import time

    from shared.schedule import parse_time

    last = parse_time(device.get("last_seen"))
    return {
        **device,
        "online": bool(last and time.time() - last.timestamp() < 90),
        "effective": resolve(manifest_for(db, device, descriptors=False)),
    }
