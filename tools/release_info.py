"""Projektversion anzeigen, gemeinsam setzen und vor einem Release prüfen."""

import argparse
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
VERSION_FIELDS = {
    "pyproject.toml": r'^version[ \t]*=[ \t]*"(?P<version>[^"\r\n]+)"',
    ".env.example": r"^KITAFENSTER_VERSION=(?P<version>[^ \t\r\n#]+)",
    "compose.yaml": r"\$\{KITAFENSTER_VERSION:-(?P<version>[^}\r\n]+)\}",
    "Dockerfile": r"^ARG APP_VERSION=(?P<version>[^ \t\r\n#]+)",
    "server/app.py": r'return \{"status": "ok", "version": "(?P<version>[^"\r\n]+)"\}',
}


def valid_version(value):
    if not isinstance(value, str) or not VERSION.fullmatch(value):
        raise ValueError("Version als drei Zahlen ohne v eingeben, zum Beispiel 0.1.3.")
    return value


def project_version(root=ROOT):
    value = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    return valid_version(value)


def version_fields(root):
    """Read every known slot before editing; retain bytes and line endings for each file."""
    root = Path(root)
    fields = []
    for name, pattern in VERSION_FIELDS.items():
        path = root / name
        original = path.read_bytes()
        content = original.decode("utf-8")
        matches = list(re.finditer(pattern, content, re.MULTILINE))
        if len(matches) != 1:
            raise ValueError(f"{name}: Genau ein Versionseintrag erwartet, {len(matches)} gefunden.")
        fields.append((path, original, content, matches[0]))
    # Ensure that the TOML slot really belongs to [project], not another table.
    if tomllib.loads(fields[0][2])["project"]["version"] != fields[0][3]["version"]:
        raise ValueError("pyproject.toml: Versionseintrag passt nicht zu [project].")
    return fields


def check_versions(root=ROOT):
    version = project_version(root)
    mismatches = [
        path.relative_to(root).as_posix()
        for path, _, _, match in version_fields(root)
        if match["version"] != version
    ]
    if mismatches:
        raise ValueError(
            f"Abweichende Projektversion in {', '.join(mismatches)}. "
            f"Mit 'python -m tools.release_info --set {version}' gemeinsam setzen."
        )
    return version


def set_version(version, root=ROOT):
    version = valid_version(version)
    changes = []
    for path, original, content, match in version_fields(root):
        start, end = match.span("version")
        updated = (content[:start] + version + content[end:]).encode("utf-8")
        if updated != original:
            changes.append((path, original, updated))
    written = []
    try:
        for path, original, updated in changes:
            written.append((path, original))
            path.write_bytes(updated)
    except OSError as error:
        failed = []
        for path, original in reversed(written):
            try:
                path.write_bytes(original)
            except OSError:
                failed.append(str(path))
        if failed:
            raise OSError(
                "Version konnte nicht vollständig zurückgesetzt werden. Dateien prüfen: " + ", ".join(failed)
            ) from error
        raise
    return [path.relative_to(root).as_posix() for path, _, _ in changes]


def validate_tag(tag, version):
    if tag != "v" + version:
        raise ValueError(f"Release-Tag muss zur Projektversion passen: v{version}")
    return version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--tag", help="Release-Tag und alle Versionsangaben prüfen, z. B. v0.1.3")
    action.add_argument(
        "--set", dest="new_version", metavar="VERSION", help="Alle Projektversionen setzen, z. B. 0.1.3"
    )
    action.add_argument("--check", action="store_true", help="Prüfen, ob alle Versionsangaben übereinstimmen")
    args = parser.parse_args()
    try:
        if args.new_version is not None:
            changed = set_version(args.new_version)
            print(f"Projektversion: {args.new_version} - {len(changed)} Dateien aktualisiert.")
            for name in changed:
                print("  " + name)
            print(f"GitHub-Release-Tag: v{args.new_version}")
            return
        version = check_versions() if args.check or args.tag is not None else project_version()
        if args.tag is not None:
            validate_tag(args.tag, version)
    except (ValueError, OSError, KeyError) as error:
        parser.error(str(error))
    print(version)


if __name__ == "__main__":
    main()
