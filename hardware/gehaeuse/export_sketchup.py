"""Gemeinsame COLLADA-XML-Hilfsfunktionen."""
import xml.etree.ElementTree as ET
NS = "http://www.collada.org/2005/11/COLLADASchema"

def element(parent, tag, text=None, **attrs):
    item = ET.SubElement(parent, f"{{{NS}}}{tag}", {k: str(v) for k, v in attrs.items()})
    if text is not None:
        item.text = str(text)
    return item
