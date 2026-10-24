"""Einrichtungsname und Logo bleiben in der lokalen, gesicherten Datenbank."""

import base64
import hashlib
import io

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_LOGO_BYTES = 2 * 1024 * 1024
MAX_LOGO_PIXELS = 4_000_000
DEFAULT_BRANDING = {"id": "site", "name": "Unsere Kita", "logo": None, "logo_hash": "default"}


def public_branding(db):
    value = db.get("branding", "site") or DEFAULT_BRANDING
    return {
        "name": value["name"],
        "custom_logo": bool(value["logo"]),
        "logo_url": "/api/branding/logo?v=" + value["logo_hash"],
    }


def normalize_logo(data, *, label="Logo", size=512):
    """Decode bounded raster input and discard metadata before publishing a PNG."""
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.format not in ("PNG", "JPEG", "WEBP") or getattr(source, "is_animated", False):
                raise ValueError("Bitte ein unbewegtes PNG-, JPEG- oder WebP-Bild wählen.")
            if source.width * source.height > MAX_LOGO_PIXELS:
                raise ValueError(f"Das {label} darf höchstens 4 Millionen Bildpunkte haben.")
            source.load()
            oriented = ImageOps.exif_transpose(source).convert("RGBA")
            oriented.thumbnail((size, size), Image.Resampling.LANCZOS)
            clean = Image.new("RGBA", oriented.size)
            clean.paste(oriented)
            buffer = io.BytesIO()
            clean.save(buffer, "PNG")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError(f"Die Datei konnte nicht als {label} gelesen werden.") from error
    normalized = buffer.getvalue()
    return {
        "logo": base64.b64encode(normalized).decode("ascii"),
        "logo_hash": hashlib.sha256(normalized).hexdigest(),
    }
