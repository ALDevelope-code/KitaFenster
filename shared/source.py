"""Source selection for releases and the web offer; excludes operator data.

New source file types or top-level build files must be added here when
extending the application. Runtime data belongs outside the source folders.
"""

import io
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT_FILES = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "LICENSE",
    "NOTICE",
    "pyproject.toml",
    "requirements-server.txt",
    "Dockerfile",
    "compose.yaml",
    "compose.build.yaml",
    ".env.example",
    ".dockerignore",
    ".gitignore",
    ".gitattributes",
)
FOLDERS = ("server", "shared", "player", "deploy", "docs", "tests", "tools")
SOURCE_SUFFIXES = {
    ".py",
    ".html",
    ".css",
    ".js",
    ".cjs",
    ".svg",
    ".md",
    ".sh",
    ".service",
    ".desktop",
    ".conf",
    ".bat",
}


def source_files(root):
    root = Path(root).resolve()
    files = [root / name for name in ROOT_FILES]
    # These build instructions form part of the corresponding source, too.
    for path in (root / ".github").rglob("*"):
        relative = path.relative_to(root / ".github")
        if path.suffix in (".yml", ".yaml", ".md") and not any(
            part.startswith(".") for part in relative.parts
        ):
            if path.is_file() and path.resolve() == path.absolute():
                files.append(path)
    for folder in FOLDERS:
        for path in (root / folder).rglob("*"):
            relative = path.relative_to(root)
            if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
                continue
            if path.suffix in SOURCE_SUFFIXES or relative.as_posix() == "deploy/player.example.json":
                if path.is_file() and path.resolve() == path.absolute():
                    files.append(path)
    for path in (root / "docs" / "screenshots").glob("*.png"):
        if path.is_file() and path.resolve() == path.absolute():
            files.append(path)
    for path in files:
        if not path.is_file() or path.resolve() != path.absolute():
            raise ValueError("Vollständiger Quellbaum erforderlich: " + path.name)
    return sorted(files)


def source_archive(root):
    root = Path(root).resolve()
    output = io.BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for path in source_files(root):
            archive.write(path, "kitafenster/" + path.relative_to(root).as_posix())
    return output.getvalue()
