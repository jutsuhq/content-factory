"""FLUX.1 Kontext [pro] on fal.ai through the synchronous https://fal.run/<model> endpoint: text-to-image for a
first frame, an edit of one reference for the rest, Kontext [max] multi when there are several references.
References go as base64 data URIs (fal decodes them); the result is a URL that is downloaded.

Docs: https://fal.ai/models/fal-ai/flux-pro/kontext/api, https://fal.ai/models/fal-ai/flux-pro/kontext/text-to-image/api,
https://fal.ai/models/fal-ai/flux-pro/kontext/max/multi/api,
https://fal.ai/docs/model-apis/model-endpoints/synchronous-requests, https://fal.ai/docs/documentation/model-apis/pricing.
"""

from __future__ import annotations

from factory.core import secrets
from factory.providers.image import web
from factory.providers.image.job import RATIOS, ImageJob

KEY = "FAL_KEY"
RUN = "https://fal.run"
TEXT, EDIT, MULTI = (
    "fal-ai/flux-pro/kontext/text-to-image",
    "fal-ai/flux-pro/kontext",
    "fal-ai/flux-pro/kontext/max/multi",
)


def _key() -> str:
    key = secrets.get(KEY)
    if not key:
        raise RuntimeError(f"{KEY} is not set")
    return key


class FalWorker:
    def __init__(self, n: int):
        self.name = f"fal-{n}"
        self.headers = {"Authorization": f"Key {_key()}"}

    def generate(self, job: ImageJob) -> None:
        payload = {"prompt": job.prompt, "aspect_ratio": RATIOS[job.shape], "output_format": "png", "num_images": 1}
        if len(job.refs) == 1:
            model, payload["image_url"] = EDIT, web.data_uri(job.refs[0])
        elif job.refs:
            model, payload["image_urls"] = MULTI, [web.data_uri(r) for r in job.refs]
        else:
            model = TEXT
        try:
            doc = web.call(f"{RUN}/{model}", self.headers, payload)
            url = doc["images"][0]["url"]
            web.save_png(web.request(url, {}), job.out)
        except (KeyError, IndexError, TypeError):
            raise RuntimeError(f"{self.name}: no image in the response") from None
        except RuntimeError as e:
            raise RuntimeError(f"{self.name}: {e}") from None

    def close(self) -> None:
        pass


def check() -> str:
    """Reads the edit model's pricing entry, which needs a valid key and costs nothing; fails on a bad key."""
    web.call(f"https://api.fal.ai/v1/models/pricing?endpoint_id={EDIT}", {"Authorization": f"Key {_key()}"})
    return "fal key works"
