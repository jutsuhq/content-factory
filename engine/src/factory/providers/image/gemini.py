"""Gemini image model ("Nano Banana") through the Interactions API: text plus base64 reference images in `input`,
the aspect ratio in `response_format`, the picture back as an image block with base64 `data`.

Docs: https://ai.google.dev/gemini-api/docs/image-generation (model ids, REST examples, aspect ratios),
https://ai.google.dev/api/interactions-api (request and content block shapes),
https://ai.google.dev/gemini-api/docs/pricing.
"""

from __future__ import annotations

import base64
import mimetypes

from factory.core import secrets
from factory.providers.image import web
from factory.providers.image.job import RATIOS, ImageJob

KEY = "GEMINI_API_KEY"
API = "https://generativelanguage.googleapis.com/v1beta"
MODEL = "gemini-nano-banana-2.1"


def _key() -> str:
    key = secrets.get(KEY)
    if not key:
        raise RuntimeError(f"{KEY} is not set")
    return key


def _image(node) -> str | None:
    """The last image block anywhere in the answer (`steps[].content[]`); generated images come after any text."""
    found = None
    if isinstance(node, dict):
        if node.get("type") == "image" and node.get("data"):
            found = node["data"]
        for v in node.values():
            found = _image(v) or found
    elif isinstance(node, list):
        for v in node:
            found = _image(v) or found
    return found


class GeminiWorker:
    def __init__(self, n: int):
        self.name = f"gemini-{n}"
        self.headers = {"x-goog-api-key": _key()}

    def generate(self, job: ImageJob) -> None:
        refs = [
            {
                "type": "image",
                "mime_type": mimetypes.guess_type(r.name)[0] or "image/png",
                "data": base64.b64encode(r.read_bytes()).decode(),
            }
            for r in job.refs
        ]
        payload = {
            "model": MODEL,
            "input": [{"type": "text", "text": job.prompt}, *refs],
            "response_format": {"type": "image", "aspect_ratio": RATIOS[job.shape]},
            "store": False,
        }
        try:
            doc = web.call(f"{API}/interactions", self.headers, payload)
        except RuntimeError as e:
            raise RuntimeError(f"{self.name}: {e}") from None
        data = _image(doc)
        if not data:
            raise RuntimeError(
                f"{self.name}: no image in the response (status {doc.get('status')}, refused or filtered?)"
            )
        web.save_png(base64.b64decode(data), job.out)

    def close(self) -> None:
        pass


def check() -> str:
    """Lists models: free, and fails on a bad key."""
    doc = web.call(f"{API}/models?pageSize=1000", {"x-goog-api-key": _key()})
    ids = {m.get("name", "").removeprefix("models/") for m in doc.get("models", [])}
    return "Gemini key works" + ("" if MODEL in ids else f", but {MODEL} is not in its model list")
