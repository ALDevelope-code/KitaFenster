"""Aufruf im Projekt: python -m tools.package_release"""

import hashlib
import os
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from shared.source import source_archive, source_files
from tools.release_info import ROOT, project_version


def package_release(root=ROOT, repository="ALDevelope-code/KitaFenster"):
    root = Path(root).resolve()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Ungültiger GitHub-Repositoryname")
    version = project_version(root)
    output = root / "dist"
    output.mkdir(exist_ok=True)
    source = output / f"kitafenster-{version}.zip"
    source.write_bytes(source_archive(root))
    nas = output / f"kitafenster-nas-{version}.zip"
    environment = (root / ".env.example").read_text(encoding="utf-8")
    environment = re.sub(r"(?m)^KITAFENSTER_VERSION=.*$", "KITAFENSTER_VERSION=" + version, environment)
    environment = re.sub(
        r"(?m)^KITAFENSTER_IMAGE=.*$", "KITAFENSTER_IMAGE=ghcr.io/" + repository.lower(), environment
    )
    with ZipFile(nas, "w", ZIP_DEFLATED) as archive:
        archive.write(root / "compose.yaml", "compose.yaml")
        archive.writestr(".env.example", environment)
        archive.writestr(
            "README.md",
            "# KitaFenster auf dem NAS\n\n"
            "[Kurzanleitung: NAS, Pi und Monitorwechsel](docs/KURZANLEITUNG.md)\n\n"
            "[NAS-Installation und Benutzerrechte](docs/INSTALLATION-NAS.md)\n",
        )
        for document in sorted((root / "docs").glob("*.md")):
            archive.write(document, "docs/" + document.name)
        archive.write(root / "tools/check_nas.py", "pruefe-nas.py")
        archive.write(root / "LICENSE", "LICENSE")
        archive.write(root / "NOTICE", "NOTICE")
    checksums = output / "SHA256SUMS"
    checksums.write_text(
        "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in (source, nas)),
        encoding="ascii",
    )
    return source, nas, checksums


if __name__ == "__main__":
    for artifact in package_release(
        repository=os.environ.get("GITHUB_REPOSITORY", "ALDevelope-code/KitaFenster")
    ):
        print(f"{artifact.name}: {artifact.stat().st_size} Bytes")
    print(f"{len(source_files(ROOT))} Quell- und Dokumentationsdateien; keine Laufzeitdaten.")
