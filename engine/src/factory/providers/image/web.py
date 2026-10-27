"""HTTP for the paid image APIs on stdlib urllib: JSON and multipart requests, one-line errors, PNG output."""

from __future__ import annotations

import base64
import io
import json
import mimetypes
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from PIL import Image

TIMEOUT = 300


def request(url: str, headers: dict[str, str], body: bytes | None = None, timeout: int = TIMEOUT) -> bytes:
    """Sends a request (POST when there is a body) and returns the response body; any failure is a RuntimeError."""
    req = urllib.request.Request(url, data=body, headers=headers, method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"http {e.code}: {_message(e.read())}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise RuntimeError(f"network: {getattr(e, 'reason', e)}") from None


def call(url: str, headers: dict[str, str], payload: dict | None = None, timeout: int = TIMEOUT) -> dict:
    """A JSON request (GET without a payload) with a JSON answer."""
    if payload is None:
        return post(url, headers, None, timeout)
    return post(url, {**headers, "Content-Type": "application/json"}, json.dumps(payload).encode(), timeout)


def post(url: str, headers: dict[str, str], body: bytes | None, timeout: int = TIMEOUT) -> dict:
    raw = request(url, headers, body, timeout)
    try:
        return json.loads(raw)
    except ValueError:
        raise RuntimeError(f"not JSON: {raw[:80]!r}") from None


def multipart(fields: list[tuple[str, str | Path]]) -> tuple[bytes, str]:
    """A multipart/form-data body; a Path value is sent as a file. Returns (body, content type)."""
    boundary = uuid.uuid4().hex
    out = io.BytesIO()
    for name, value in fields:
        out.write(f"--{boundary}\r\n".encode())
        if isinstance(value, Path):
            kind = mimetypes.guess_type(value.name)[0] or "application/octet-stream"
            out.write(
                f'Content-Disposition: form-data; name="{name}"; filename="{value.name}"\r\n'
                f"Content-Type: {kind}\r\n\r\n".encode()
            )
            out.write(value.read_bytes())
        else:
            out.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}'.encode())
        out.write(b"\r\n")
    out.write(f"--{boundary}--\r\n".encode())
    return out.getvalue(), f"multipart/form-data; boundary={boundary}"


def data_uri(path: Path) -> str:
    kind = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{kind};base64,{base64.b64encode(path.read_bytes()).decode()}"


def save_png(data: bytes, out: Path) -> None:
    """Whatever format the API returned, the job gets a PNG."""
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:
        raise RuntimeError(f"not an image: {data[:80]!r}") from None
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "PNG")


def _message(raw: bytes) -> str:
    """The error text from the usual JSON shapes ({error: {message}}, {error: "..."}, {detail}), else the raw body."""
    try:
        doc = json.loads(raw)
    except ValueError:
        return " ".join(raw.decode(errors="replace").split())[:200]
    err = doc.get("error", doc.get("detail", doc)) if isinstance(doc, dict) else doc
    if isinstance(err, dict):
        return " ".join(str(err.get(k)) for k in ("code", "status", "message") if err.get(k))[:300]
    if isinstance(err, list) and err and isinstance(err[0], dict):
        return str(err[0].get("msg", err[0]))[:300]
    return str(err)[:300]
