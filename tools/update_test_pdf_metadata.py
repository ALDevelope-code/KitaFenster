"""Normalize the metadata of the neutral PDF fixtures."""

from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

ROOT = Path(__file__).resolve().parents[1]


def update(path: Path) -> None:
    reader = PdfReader(path)
    writer = PdfWriter()
    for page in reader.pages:
        contents = page.get_contents()
        data = contents.get_data()
        if b"KITAFENSTER" not in data:
            raise RuntimeError(f"KitaFenster-Kopfzeile fehlt in {path}")
        stream = DecodedStreamObject()
        stream.set_data(data)
        page[NameObject("/Contents")] = stream
        writer.add_page(page)
    writer.add_metadata(
        {
            "/Author": "KitaFenster - fiktive Beispieldaten",
            "/Creator": "KitaFenster",
            "/Producer": "pypdf",
            "/Title": "Fiktiver Elternplan",
        }
    )
    temporary = path.with_suffix(".tmp.pdf")
    with temporary.open("wb") as stream:
        writer.write(stream)
    temporary.replace(path)


def main() -> None:
    paths = sorted((ROOT / "testdaten").glob("Gruppe */Infos/Elternplan.pdf"))
    if len(paths) != 3:
        raise RuntimeError(f"Drei Elternplan-PDFs erwartet, {len(paths)} gefunden")
    for path in paths:
        update(path)
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
