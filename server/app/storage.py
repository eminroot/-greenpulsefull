"""Leaf images on disk.

Kept as plain files under GP_DATA_DIR rather than in the database: they are
written once, read occasionally, and a Contabo volume is the cheapest place for
them. Paths are always derived from ids we generated, never from anything a
node or a phone sent, so a crafted filename cannot escape the directory.
"""

from __future__ import annotations

import base64
import binascii
import re
from pathlib import Path

from .config import settings

# A node sends JPEG; a phone may send either. Type is decided by these bytes,
# never by a filename the caller supplied.
_MAGIC = (
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
)


def _is_webp(data: bytes) -> bool:
    # "RIFF" alone also starts .wav and .avi, so the form type is checked too.
    return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"


class ImageTooLarge(Exception):
    pass


class UnsupportedImage(Exception):
    pass


class UnsafeName(Exception):
    pass


# Filenames are built from ids, so anything outside this set is either a bug or
# an attempt to escape the directory.
_SAFE_KEY = re.compile(r"^[A-Za-z0-9._-]{1,120}$")


def safe_key(value: str) -> str:
    """Refuses a key that could climb out of the data directory.

    The capture id in an ingest body comes from the greenhouse node, which means
    a compromised node or a leaked device token could otherwise ask us to write
    to `../../../etc/...`. Path components are rejected outright rather than
    stripped, so a surprising id is a visible error instead of a silent rename.
    """
    if not value or not _SAFE_KEY.match(value) or value in {".", ".."}:
        raise UnsafeName(f"Unsafe storage key: {value!r}")
    return value


def sniff_extension(data: bytes) -> str:
    """Identify the image by its bytes, never by a name the caller supplied."""
    for magic, ext in _MAGIC:
        if data.startswith(magic):
            return ext
    if _is_webp(data):
        return "webp"
    raise UnsupportedImage("Expected a JPEG, PNG or WebP image")


def decode_base64(value: str) -> bytes:
    payload = value.split(",", 1)[-1] if value.startswith("data:") else value
    try:
        return base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise UnsupportedImage("Image is not valid base64") from exc


def _relative(site_id: str, kind: str, key: str, ext: str) -> str:
    return f"{site_id}/{kind}/{key}.{ext}"


def save_image(data: bytes, *, site_id: str, kind: str, key: str) -> tuple[str, int]:
    """Write bytes and return (relative_path, size). kind is 'captures' or 'scans'."""
    if len(data) > settings.max_image_bytes:
        raise ImageTooLarge(
            f"Image is {len(data)} bytes, limit is {settings.max_image_bytes}"
        )
    if not data:
        raise UnsupportedImage("Empty image")

    if kind not in {"captures", "scans"}:
        raise UnsafeName(f"Unknown storage kind: {kind!r}")

    ext = sniff_extension(data)
    rel = _relative(safe_key(site_id), kind, safe_key(key), ext)

    root = settings.data_dir.resolve()
    path = (root / rel).resolve()
    # Belt and braces: even with the key checked, never write outside the root.
    if root not in path.parents:
        raise UnsafeName(f"Refusing to write outside the data directory: {rel}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return rel, len(data)


def resolve(relative_path: str) -> Path | None:
    """Turn a stored relative path back into a file, refusing anything that
    points outside the data directory."""
    if not relative_path:
        return None
    root = settings.data_dir.resolve()
    candidate = (root / relative_path).resolve()
    if root not in candidate.parents and candidate != root:
        return None
    return candidate if candidate.is_file() else None


def delete(relative_path: str | None) -> None:
    if not relative_path:
        return
    path = resolve(relative_path)
    if path:
        path.unlink(missing_ok=True)


def content_type_for(path: Path) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "application/octet-stream")
