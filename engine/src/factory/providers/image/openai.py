"""OpenAI GPT Image: /v1/images/generations for text, /v1/images/edits (multipart, one `image[]` per reference)
for edits.

Docs: https://developers.openai.com/api/docs/guides/image-generation.md (endpoints, sizes, quality, b64_json),
https://developers.openai.com/api/docs/models.md (model ids), https://developers.openai.com/api/docs/pricing.md.
"""

from __future__ import annotations

import base64

from factory.core import secrets
from factory.providers.image import web
from factory.providers.image.job import SIZES, ImageJob

KEY = "OPENAI_API_KEY"
API = "https://api.openai.com/v1"
# "the most capable model for generating and editing images" in the model list; gpt-image-2 is the cheaper fallback
MODEL = "gpt-image-2.5-sunburst"
QUALITY = "medium"


def _key() -> str:
    key = secrets.get(KEY)
    if not key:
        raise RuntimeError(f"{KEY} is not set")
    return key


class OpenAIWorker:
    def __init__(self, n: int):
        self.name = f"openai-{n}"
        self.headers = {"Authorization": f"Bearer {_key()}"}

    def generate(self, job: ImageJob) -> None:
        params = {"model": MODEL, "prompt": job.prompt, "size": SIZES[job.shape], "quality": QUALITY}
        try:
            if job.refs:
                body, kind = web.multipart([*params.items(), *(("image[]", ref) for ref in job.refs)])
                doc = web.post(f"{API}/images/edits", {**self.headers, "Content-Type": kind}, body)
            else:
                doc = web.call(f"{API}/images/generations", self.headers, params)
            web.save_png(base64.b64decode(doc["data"][0]["b64_json"]), job.out)
        except (KeyError, IndexError, TypeError):
            raise RuntimeError(f"{self.name}: no image in the response") from None
        except RuntimeError as e:
            raise RuntimeError(f"{self.name}: {e}") from None

    def close(self) -> None:
        pass


def check() -> str:
    """Lists models: free, and fails on a bad key."""
    doc = web.call(f"{API}/models", {"Authorization": f"Bearer {_key()}"})
    ids = {m.get("id") for m in doc.get("data", [])}
    return "OpenAI key works" + (
        "" if MODEL in ids else f", but {MODEL} is not available to it (verify the organization)"
    )
