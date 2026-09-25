"""Reading an uploaded file without trusting how big it is.

`await upload.read()` pulls the whole body into memory before anything has a
chance to check its size, so a single large POST could push the process into
swap or out of memory. Caddy caps request bodies in production, but the API is
also reachable directly in development and on a LAN, and a limit that only
exists in the proxy is a limit that disappears the moment someone runs the
container on its own.
"""

from __future__ import annotations

from fastapi import HTTPException, UploadFile

from .config import settings

CHUNK = 64 * 1024


async def read_upload(upload: UploadFile, limit: int | None = None) -> bytes:
    """Read an upload, refusing anything over the limit as it arrives."""
    cap = limit if limit is not None else settings.max_image_bytes

    # A declared length is a hint, not a promise, so it only short circuits the
    # obvious case. The real enforcement is the running total below.
    declared = upload.size
    if declared is not None and declared > cap:
        raise HTTPException(status_code=413, detail="image_too_large")

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > cap:
            raise HTTPException(status_code=413, detail="image_too_large")
        chunks.append(chunk)

    return b"".join(chunks)
