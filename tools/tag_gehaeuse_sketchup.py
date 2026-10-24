"""Assign one SketchUp tag per housing group, organized in tag folders.

Run this after generating hardware/gehaeuse/gehaeuse_*.skp. SketchUp calls
them layers in its C API, although the application displays them as tags.
"""

from __future__ import annotations

import argparse
import ctypes as c
import os
from pathlib import Path
import shutil
import tempfile


class Ref(c.Structure):
    _fields_ = [("ptr", c.c_void_p)]


def category(name: str) -> str:
    if name.startswith(("Front_", "Rueckseite_")):
        return "Gehäuse"
    if name.startswith("Andruckteller_"):
        return "Halter"
    if name.startswith("Klebekeil_"):
        return "Anbauteile"
    if name.startswith("REFERENZ_"):
        return "Referenzen"
    raise ValueError(f"Unbekannte SketchUp-Gruppe: {name}")


def tag_model(api: c.CDLL, source: Path, target: Path) -> tuple[list[str], bool]:
    ref_pointer = c.POINTER(Ref)
    size_pointer = c.POINTER(c.c_size_t)

    def bind(name: str, arguments: list[object], result: object = c.c_int) -> object:
        function = getattr(api, name)
        function.argtypes = arguments
        function.restype = result
        return function

    for name, arguments in {
        "SUModelCreateFromFile": [ref_pointer, c.c_char_p],
        "SUModelRelease": [ref_pointer],
        "SUModelGetEntities": [Ref, ref_pointer],
        "SUModelGetDefaultLayer": [Ref, ref_pointer],
        "SUEntitiesGetNumGroups": [Ref, size_pointer],
        "SUEntitiesGetGroups": [Ref, c.c_size_t, ref_pointer, size_pointer],
        "SUGroupGetName": [Ref, ref_pointer],
        "SUDrawingElementGetLayer": [Ref, ref_pointer],
        "SULayerGetName": [Ref, ref_pointer],
        "SULayerGetParentLayerFolder": [Ref, ref_pointer],
        "SULayerFolderGetName": [Ref, ref_pointer],
        "SUStringCreate": [ref_pointer],
        "SUStringGetUTF8Length": [Ref, size_pointer],
        "SUStringGetUTF8": [Ref, c.c_size_t, c.c_char_p, size_pointer],
        "SUStringRelease": [ref_pointer],
        "SULayerFolderCreate": [ref_pointer, c.c_char_p],
        "SUModelAddLayerFolder": [Ref, Ref],
        "SULayerCreate": [ref_pointer],
        "SULayerSetName": [Ref, c.c_char_p],
        "SUModelAddLayers": [Ref, c.c_size_t, ref_pointer],
        "SULayerFolderAddLayer": [Ref, Ref],
        "SUDrawingElementSetLayer": [Ref, Ref],
        "SUModelSaveToFile": [Ref, c.c_char_p],
    }.items():
        bind(name, arguments)
    bind("SUGroupToDrawingElement", [Ref], Ref)

    def call(name: str, *arguments: object) -> None:
        result = getattr(api, name)(*arguments)
        if result != 0:
            raise RuntimeError(f"{name}: SketchUp-Fehler {result}")

    def reference_name(getter: str, reference: Ref) -> str:
        string = Ref()
        call("SUStringCreate", c.byref(string))
        try:
            call(getter, reference, c.byref(string))
            length = c.c_size_t()
            call("SUStringGetUTF8Length", string, c.byref(length))
            buffer = c.create_string_buffer(length.value + 1)
            written = c.c_size_t()
            call("SUStringGetUTF8", string, len(buffer), buffer, c.byref(written))
            return buffer.value.decode("utf-8")
        finally:
            call("SUStringRelease", c.byref(string))

    model = Ref()
    call("SUModelCreateFromFile", c.byref(model), str(source).encode("utf-8"))
    try:
        entities = Ref()
        call("SUModelGetEntities", model, c.byref(entities))
        count = c.c_size_t()
        call("SUEntitiesGetNumGroups", entities, c.byref(count))
        groups = (Ref * count.value)()
        written = c.c_size_t()
        call("SUEntitiesGetGroups", entities, count.value, groups, c.byref(written))

        default_layer = Ref()
        call("SUModelGetDefaultLayer", model, c.byref(default_layer))
        existing_tags = 0
        for group in groups[: written.value]:
            name = reference_name("SUGroupGetName", group)
            layer = Ref()
            call("SUDrawingElementGetLayer", api.SUGroupToDrawingElement(group), c.byref(layer))
            if layer.ptr == default_layer.ptr:
                continue
            existing_tags += 1
            tag_name = reference_name("SULayerGetName", layer)
            folder = Ref()
            call("SULayerGetParentLayerFolder", layer, c.byref(folder))
            folder_name = reference_name("SULayerFolderGetName", folder)
            if tag_name != name or folder_name != category(name):
                raise ValueError(f"Abweichende Tag-Zuordnung für {name}: {folder_name}/{tag_name}")

        if existing_tags:
            if existing_tags != written.value:
                raise ValueError(f"Nur ein Teil der Gruppen hat Tags: {source}")
            return [reference_name("SUGroupGetName", group) for group in groups[: written.value]], False

        folders: dict[str, Ref] = {}
        names: list[str] = []
        for group in groups[: written.value]:
            name = reference_name("SUGroupGetName", group)
            folder_name = category(name)
            if name in names:
                raise ValueError(f"Doppelter Gruppenname: {name}")
            names.append(name)

            if folder_name not in folders:
                folder = Ref()
                call("SULayerFolderCreate", c.byref(folder), folder_name.encode("utf-8"))
                call("SUModelAddLayerFolder", model, folder)
                folders[folder_name] = folder

            layer = Ref()
            call("SULayerCreate", c.byref(layer))
            call("SULayerSetName", layer, name.encode("utf-8"))
            call("SUModelAddLayers", model, 1, c.byref(layer))
            call("SULayerFolderAddLayer", folders[folder_name], layer)
            call("SUDrawingElementSetLayer", api.SUGroupToDrawingElement(group), layer)

        if not names:
            raise ValueError(f"Keine Gruppen gefunden: {source}")
        call("SUModelSaveToFile", model, str(target).encode("utf-8"))
        return names, True
    finally:
        call("SUModelRelease", c.byref(model))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api",
        type=Path,
        default=Path("C:/Program Files/SketchUp/SketchUp 2026/SketchUp/SketchUpAPI.dll"),
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        default=[
            Path("hardware/gehaeuse/gehaeuse_geteilt.skp"),
            Path("hardware/gehaeuse/gehaeuse_komplett.skp"),
        ],
    )
    args = parser.parse_args()

    dll_directory = os.add_dll_directory(str(args.api.parent))
    api = c.CDLL(str(args.api))
    api.SUInitialize.argtypes = []
    api.SUInitialize.restype = None
    api.SUTerminate.argtypes = []
    api.SUTerminate.restype = None
    api.SUInitialize()
    try:
        for source in args.files:
            source = source.resolve(strict=True)
            with tempfile.TemporaryDirectory(prefix="kitafenster-skp-tags-") as directory:
                target = Path(directory) / source.name
                names, changed = tag_model(api, source, target)
                if changed:
                    shutil.copyfile(target, source)
            print(f"{source.name}: {len(names)} Gruppen mit eigenen Tags")
    finally:
        api.SUTerminate()
        dll_directory.close()


if __name__ == "__main__":
    main()
