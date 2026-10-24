"""Containerrechte prüfen: python -m tools.check_nas [Gruppenordner ...]."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

MEDIA_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".pdf"}


def check_access(nas_root, data_dir, groups):
    nas_root, data_dir = Path(nas_root), Path(data_dir)
    with (nas_root / ".bilderrahmen-source").open("rb") as stream:
        stream.read(1)
    print("NAS-Marker: lesbar")

    def fail(error):
        raise error

    for group in groups:
        folder = (nas_root / group).resolve()
        if not folder.is_relative_to(nas_root.resolve()):
            raise ValueError("Gruppenordner muss innerhalb der NAS-Quelle liegen")
        count = 0
        for directory, dirs, names in os.walk(folder, onerror=fail, followlinks=False):
            dirs[:] = [
                d for d in dirs if not d.startswith((".", "@")) and not (Path(directory) / d).is_symlink()
            ]
            for name in names:
                path = Path(directory) / name
                if name.startswith((".", "@")) or path.is_symlink():
                    continue
                if path.suffix.lower() in MEDIA_SUFFIXES:
                    with path.open("rb") as stream:
                        stream.read(1)
                    count += 1
        print(f"{group}: {count} Bild-/PDF-Dateien lesbar")

    # Check the mounted data directory itself; do not create a missing mount.
    with tempfile.TemporaryFile(dir=data_dir) as stream:
        stream.write(b"KitaFenster Schreibpruefung")
        stream.flush()
        os.fsync(stream.fileno())
    print("/data: Schreiben erfolgreich; Testdatei entfernt")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("groups", nargs="*", default=["Gruppe 1", "Gruppe 2", "Gruppe 3"])
    args = parser.parse_args()
    try:
        check_access(os.environ.get("NAS_ROOT", "/nas"), os.environ.get("DATA_DIR", "/data"), args.groups)
    except (OSError, ValueError) as error:
        print(f"Zugriffsprüfung fehlgeschlagen: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
