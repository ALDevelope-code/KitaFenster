"""Document references and atomic removal of a document and its assignments."""

import hashlib
import json

from fastapi import HTTPException

from server.db import Database


def list_assignment(document, groups):
    return document.get(
        "list_assignment",
        {
            "all_groups": False,
            "group_ids": [
                g["id"] for g in groups if g.get("plan_id") == document["id"] and not g.get("plan_path")
            ],
        },
    )


def save_document_metadata(db, document_id, changes):
    changes = dict(changes)
    revoke = changes.pop("revoke_group_release", False)
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        document = _required(connection, "document", document_id)
        revoke_groups = document.get("public", False) != changes["public"] or (
            revoke and not changes["public"]
        )
        if revoke_groups:
            document["parent_groups"] = []
            if not changes["public"]:
                for row in connection.execute("SELECT data FROM entities WHERE kind='group'"):
                    group = json.loads(row[0])
                    if (
                        group.get("plan_id") == document_id
                        and not group.get("plan_path")
                        and group.get("plan_public")
                    ):
                        group["plan_public"] = False
                        Database.write(connection, "group", group)
        document.update(changes)
        Database.write(connection, "document", document)
    return document


def save_list_assignment(db, document_id, assignment):
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        document = _required(connection, "document", document_id)
        if document["kind"] != "plan":
            raise HTTPException(422, "Bitte ein Dokument auswählen")
        for group_id in assignment["group_ids"]:
            _required(connection, "group", group_id)
        document["list_assignment"] = {
            "all_groups": assignment["all_groups"],
            "group_ids": [] if assignment["all_groups"] else sorted(set(assignment["group_ids"])),
        }
        # Retire old single-document links without changing NAS permissions.
        for row in connection.execute("SELECT data FROM entities WHERE kind='group'").fetchall():
            group = json.loads(row[0])
            if group.get("plan_id") == document_id:
                if group.get("plan_public") and not group.get("plan_path"):
                    document["parent_groups"] = sorted(set(document.get("parent_groups", []) + [group["id"]]))
                _unlink_group(group)
                Database.write(connection, "group", group)
        Database.write(connection, "document", document)
        return document


def migrate_document_lists(db):
    """Preserve old uploads and NAS sources, without broadening their audience."""
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        groups = [
            json.loads(r[0]) for r in connection.execute("SELECT data FROM entities WHERE kind='group'")
        ]
        for group in groups:
            if group.get("document_list_migrated"):
                continue
            if not group.get("plan_path") and not group.get("plan_id"):
                continue
            if group.get("plan_path"):
                snapshot = connection.execute(
                    "SELECT data FROM entities WHERE kind='snapshot' AND id=?", (group["id"],)
                ).fetchone()
                snapshot = json.loads(snapshot[0]) if snapshot else {}
                assets = (
                    snapshot.get("plan", [])
                    if snapshot.get("folder") == group["folder"]
                    and snapshot.get("plan_path") == group["plan_path"]
                    else []
                )
                if group.get("plan_public") and not snapshot.get("plan_public"):
                    assets = []  # Re-read the NAS source before applying a newly granted permission.
                Database.write(
                    connection,
                    "document",
                    {
                        "id": "nas-" + group["id"],
                        "kind": "plan",
                        "name": group["plan_path"].replace("\\", "/").split("/")[-1],
                        "category": "Dokument",
                        "public": False,
                        "assets": assets,
                        "created_at": snapshot.get("last_sync"),
                        "legacy_nas_group": group["id"],
                        "legacy_nas_folder": group["folder"],
                        "legacy_nas_path": group["plan_path"],
                        "parent_groups": [group["id"]] if group.get("plan_public") else [],
                        "list_assignment": {"all_groups": False, "group_ids": [group["id"]]},
                    },
                )
                group["plan_id"] = None
            elif group.get("plan_id"):
                row = connection.execute(
                    "SELECT data FROM entities WHERE kind='document' AND id=?", (group["plan_id"],)
                ).fetchone()
                if row:
                    document = json.loads(row[0])
                    assignment = document.setdefault(
                        "list_assignment", {"all_groups": False, "group_ids": []}
                    )
                    if group["id"] not in assignment["group_ids"]:
                        assignment["group_ids"].append(group["id"])
                    if group.get("plan_public"):
                        document["parent_groups"] = sorted(
                            set(document.get("parent_groups", []) + [group["id"]])
                        )
                    Database.write(connection, "document", document)
                _unlink_group(group)
            group["document_list_migrated"] = True
            Database.write(connection, "group", group)


def _required(connection, kind, id):
    row = connection.execute("SELECT data FROM entities WHERE kind=? AND id=?", (kind, id)).fetchone()
    if row is None:
        raise HTTPException(404, "Eintrag nicht gefunden")
    return json.loads(row[0])


def _usage(connection, id):
    document = _required(connection, "document", id)
    references = []
    assignment = document.get("list_assignment", {})
    if assignment.get("all_groups") or assignment.get("group_ids"):
        references.append(
            {
                "kind": "document_list",
                "id": id,
                "slot": json.dumps(assignment, sort_keys=True),
                "label": "Gemeinsame Dokumentenliste",
            }
        )
    for row in connection.execute(
        "SELECT kind,id,data FROM entities WHERE kind IN ('group','notice','device') ORDER BY kind,id"
    ):
        kind, target_id, value = row["kind"], row["id"], json.loads(row["data"])
        name = value.get("name", value.get("title", target_id))

        def add(slot, label):
            references.append({"kind": kind, "id": target_id, "slot": slot, "label": label})

        if kind == "group" and value.get("plan_id") == id:
            add("group", "Gruppe: " + name)
        elif kind == "notice" and value.get("image_id") == id:
            add("image", "Meldungsbild: " + name)
        elif kind == "device":
            settings = value["settings"]
            if settings.get("document_id") == id:
                add("default", "Bilderrahmen: " + name + " · Standardanzeige")
            for index, hour in enumerate(settings.get("content_windows", [])):
                if hour.get("document_id") == id:
                    title = hour.get("name") or str(index + 1)
                    if hour.get("area") == "secondary":
                        title += " (Zusätzliche Anzeige)"
                    add("hour:" + str(index), "Bilderrahmen: " + name + " · Anzeigezeit " + title)
            for index, entry in enumerate(settings.get("playlist", [])):
                if entry.get("document_id") == id:
                    add(
                        "playlist:" + str(index),
                        "Bilderrahmen: " + name + " · Gemischt, Eintrag " + str(index + 1),
                    )
            secondary = settings.get("split", {}).get("secondary", {})
            if secondary.get("document_id") == id:
                add("secondary", "Bilderrahmen: " + name + " · Zusätzliche Anzeige")
            for index, entry in enumerate(secondary.get("playlist", [])):
                if entry.get("document_id") == id:
                    add(
                        "secondary-playlist:" + str(index),
                        "Bilderrahmen: " + name + " · Zusätzliche Anzeige, Eintrag " + str(index + 1),
                    )
    revision = hashlib.sha256(json.dumps(references, sort_keys=True).encode()).hexdigest()
    return {"document": {"id": id, "name": document["name"]}, "references": references, "revision": revision}


def document_usage(db, id):
    with db.connect() as connection:
        connection.execute("BEGIN")
        return _usage(connection, id)


def _unlink_group(group):
    group["plan_id"] = None
    # The public flag may belong to the active NAS file, not the removed upload.
    if not group.get("plan_path"):
        group["plan_public"] = False


def unlink_group(db, document_id, group_id):
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        group = _required(connection, "group", group_id)
        if group.get("plan_id") != document_id:
            raise HTTPException(409, "Die Gruppenzuordnung wurde inzwischen geändert. Bitte neu öffnen.")
        _unlink_group(group)
        Database.write(connection, "group", group)
        return group


def update_all_group_assignments(db, document_id, *, assign, plan_public=False):
    """Apply the complete group operation atomically; never delete the document."""
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        document = _required(connection, "document", document_id)
        if document["kind"] != "plan":
            raise HTTPException(422, "Bitte ein Dokument auswählen")
        groups = [
            json.loads(row[0])
            for row in connection.execute("SELECT data FROM entities WHERE kind='group' ORDER BY id")
        ]
        changed = []
        for group in groups:
            if assign:
                group["plan_id"] = document_id
                # A NAS file keeps its own existing permission and display precedence.
                if not group.get("plan_path"):
                    group["plan_public"] = plan_public
            elif group.get("plan_id") == document_id:
                _unlink_group(group)
            else:
                continue
            Database.write(connection, "group", group)
            changed.append(group["id"])
        return {"ok": True, "groups": changed}


def _clear_selection(value, id, mode_key="mode"):
    if value.get("document_id") != id:
        return False
    value["document_id"] = None
    if value.get(mode_key) == "plan":
        value[mode_key] = "photos"
    return True


def delete_document(db, id, *, unlink=False, revision=None):
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        usage = _usage(connection, id)
        if revision is not None and revision != usage["revision"]:
            raise HTTPException(
                409, "Die Zuordnungen wurden inzwischen geändert. Bitte den Löschdialog neu öffnen."
            )
        if usage["references"] and not unlink:
            raise HTTPException(
                409,
                "Datei wird noch verwendet. Bitte zuerst die Zuordnungen lösen oder das gemeinsame Löschen bestätigen.",
            )
        if usage["references"] and not revision:
            raise HTTPException(409, "Bitte die aktuellen Zuordnungen im Löschdialog prüfen und bestätigen.")
        for kind, target_id in sorted({(ref["kind"], ref["id"]) for ref in usage["references"]}):
            if kind == "document_list":
                continue  # Membership is stored with the document being deleted.
            value = _required(connection, kind, target_id)
            if kind == "group":
                _unlink_group(value)
            elif kind == "notice":
                value["image_id"] = None
            elif kind == "device":
                settings = value["settings"]
                secondary = settings.get("split", {}).get("secondary", {})
                if _clear_selection(secondary, id, "default_mode"):
                    if (value.get("manual_secondary") or {}).get("mode") == "plan":
                        value["manual_secondary"] = None
                if secondary.get("playlist"):
                    secondary["playlist"] = [
                        entry
                        for entry in secondary["playlist"]
                        if not (entry.get("document_id") == id and entry["mode"] == "plan")
                    ] or [{"mode": "photos", "seconds": secondary.get("interval", 12), "document_id": None}]
                    for entry in secondary["playlist"]:
                        _clear_selection(entry, id)
                if (
                    _clear_selection(settings, id, "default_mode")
                    and (value.get("manual") or {}).get("mode") == "plan"
                ):
                    value["manual"] = None
                for hour in settings.get("content_windows", []):
                    _clear_selection(hour, id)
                playlist = settings.get("playlist", [])
                kept = [
                    entry
                    for entry in playlist
                    if not (entry.get("document_id") == id and entry["mode"] == "plan")
                ]
                for entry in kept:
                    _clear_selection(entry, id)
                if playlist:
                    settings["playlist"] = kept or [
                        {"mode": "photos", "seconds": settings.get("interval", 12), "document_id": None}
                    ]
            Database.write(connection, kind, value)
        connection.execute("DELETE FROM entities WHERE kind='document' AND id=?", (id,))
        return {"ok": True, "unlinked": len(usage["references"])}
