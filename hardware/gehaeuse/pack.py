"""Package the final enclosure and verify archived files and SHA256 hashes."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

BASE = Path(__file__).resolve().parent
OUT = BASE / 'gehaeuse_sketchup_und_druck.zip'
MANIFEST = BASE / 'lieferumfang_sha256.json'
files = sorted(p for p in BASE.rglob('*') if p.is_file()
               and '__pycache__' not in p.parts
               # Individuell bemalte Slicerprojekte werden nicht automatisch aktualisiert.
               and 'Bambu_Projekte' not in p.parts
               and p.suffix not in ('.skb', '.bak', '.pyc', '.zip')
               and p != MANIFEST)
assert len([p for p in files if p.suffix == '.stl']) == 10
assert len([p for p in files if p.suffix == '.skp']) == 3
for report, success in [
    ('kollisionspruefung.txt', 'Alle digitalen Schnitt- und Formatpruefungen bestanden.'),
    ('gewindepruefung.txt', 'Alle digitalen Gewindepruefungen bestanden.'),
    ('frontpassung_pruefung.txt', 'Alle digitalen Frontpassungspruefungen bestanden.'),
    ('deckelgewinde_pruefung.txt', 'Alle digitalen Deckelgewinde-Pruefungen bestanden.'),
]:
    assert success in (BASE / report).read_text(encoding='utf-8'), report
for mode, count in [('geteilt', 19), ('komplett', 10), ('M4', 1)]:
    report = (BASE / f'sketchup_pruefung_{mode}.txt').read_text(encoding='utf-8')
    assert report.count('Nach erneutem Laden:') == count
for target in re.findall(r'\]\(([^)]+)\)', (BASE/'README.md').read_text(encoding='utf-8')):
    if not target.startswith(('https://', 'http://', '#')) and target not in (MANIFEST.name, OUT.name):
        assert (BASE / target).is_file(), target
entries = {p.relative_to(BASE).as_posix(): p.read_bytes() for p in files}
hashes = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(entries.items())}
manifest = json.dumps({'algorithm': 'SHA256', 'self_excluded': True, 'files': hashes}, indent=2).encode('utf-8')
MANIFEST.write_bytes(manifest)
entries[MANIFEST.name] = manifest
with zipfile.ZipFile(OUT, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for name, data in sorted(entries.items()):
        archive.writestr(name, data)
with zipfile.ZipFile(OUT) as archive:
    assert archive.testzip() is None
    assert set(archive.namelist()) == set(entries)
    for name, digest in hashes.items():
        assert hashlib.sha256(archive.read(name)).hexdigest() == digest, name
print(f'{OUT.name}: {len(entries)} Dateien; CRC und alle SHA256-Pruefsummen stimmen.')
