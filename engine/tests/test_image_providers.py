"""The paid image providers against a fake urlopen: the request each one sends and the PNG it writes. No network."""

import base64
import io
import json
import urllib.error

import pytest
from PIL import Image

from factory.providers.image import ImageJob, available, catalog, check, web
from factory.providers.image.fal import FalWorker
from factory.providers.image.gemini import GeminiWorker
from factory.providers.image.openai import OpenAIWorker
from factory.providers.image.pool import FATAL


def picture(fmt="PNG", size=(4, 6)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "red").save(buf, fmt)
    return buf.getvalue()


class Fake:
    """Stands in for urlopen: records each Request and answers with the next queued body (or raises it)."""

    def __init__(self, *answers):
        self.answers, self.seen = list(answers), []

    def __call__(self, req, timeout=None):
        self.seen.append(req)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        body = answer if isinstance(answer, bytes) else json.dumps(answer).encode()
        return io.BytesIO(body)

    def json(self, i=0):
        return json.loads(self.seen[i].data)


@pytest.fixture
def keys(monkeypatch):
    for k, v in {"OPENAI_API_KEY": "sk-test", "GEMINI_API_KEY": "g-test", "FAL_KEY": "f-test"}.items():
        monkeypatch.setenv(k, v)


def fake(monkeypatch, *answers) -> Fake:
    f = Fake(*answers)
    monkeypatch.setattr(web.urllib.request, "urlopen", f)
    return f


def is_png(path, size=(4, 6)):
    with Image.open(path) as im:
        return im.format == "PNG" and im.size == size


def test_openai_text_posts_json_with_the_size_of_the_shape(keys, monkeypatch, tmp_path):
    f = fake(monkeypatch, {"data": [{"b64_json": base64.b64encode(picture()).decode()}]})
    job = ImageJob("a barn", tmp_path / "f1.png", shape="l")
    OpenAIWorker(1).generate(job)
    req = f.seen[0]
    assert req.full_url == "https://api.openai.com/v1/images/generations" and req.get_method() == "POST"
    assert req.get_header("Authorization") == "Bearer sk-test"
    assert f.json() == {"model": "gpt-image-2.5-sunburst", "prompt": "a barn", "size": "1536x1024", "quality": "medium"}
    assert is_png(job.out)


def test_openai_edit_sends_every_reference_as_image_array_in_multipart(keys, monkeypatch, tmp_path):
    refs = [tmp_path / "frame1.png", tmp_path / "hero.jpg"]
    refs[0].write_bytes(picture())
    refs[1].write_bytes(picture("JPEG"))
    f = fake(monkeypatch, {"data": [{"b64_json": base64.b64encode(picture()).decode()}]})
    OpenAIWorker(1).generate(ImageJob("same barn, night", tmp_path / "f2.png", refs=refs))
    req = f.seen[0]
    assert req.full_url == "https://api.openai.com/v1/images/edits"
    kind = req.get_header("Content-type")
    assert kind.startswith("multipart/form-data; boundary=")
    body = req.data
    assert body.count(b'name="image[]"') == 2
    assert b'filename="frame1.png"\r\nContent-Type: image/png' in body and b"Content-Type: image/jpeg" in body
    assert b'name="size"\r\n\r\n1024x1536\r\n' in body and b'name="model"\r\n\r\ngpt-image-2.5-sunburst' in body
    assert body.rstrip().endswith(f"--{kind.split('=')[1]}--".encode())
    assert is_png(tmp_path / "f2.png")


def test_gemini_sends_refs_inline_and_asks_for_the_ratio(keys, monkeypatch, tmp_path):
    ref = tmp_path / "frame1.png"
    ref.write_bytes(picture())
    answer = {
        "status": "completed",
        "steps": [
            {
                "type": "model_output",
                "content": [
                    {"type": "text", "text": "Here it is"},
                    {"type": "image", "mime_type": "image/jpeg", "data": base64.b64encode(picture("JPEG")).decode()},
                ],
            }
        ],
    }
    f = fake(monkeypatch, answer)
    GeminiWorker(1).generate(ImageJob("same barn, snow", tmp_path / "f2.png", refs=[ref]))
    req = f.seen[0]
    assert req.full_url == "https://generativelanguage.googleapis.com/v1beta/interactions"
    assert req.get_header("X-goog-api-key") == "g-test"
    body = f.json()
    assert body["model"] == "gemini-nano-banana-2.1"
    assert body["input"] == [
        {"type": "text", "text": "same barn, snow"},
        {"type": "image", "mime_type": "image/png", "data": base64.b64encode(picture()).decode()},
    ]
    assert body["response_format"] == {"type": "image", "aspect_ratio": "2:3"}
    assert is_png(tmp_path / "f2.png")  # a JPEG answer still lands as PNG


def test_gemini_without_an_image_says_so(keys, monkeypatch, tmp_path):
    fake(
        monkeypatch,
        {"status": "completed", "steps": [{"type": "model_output", "content": [{"type": "text", "text": "no"}]}]},
    )
    with pytest.raises(RuntimeError, match="no image"):
        GeminiWorker(1).generate(ImageJob("x", tmp_path / "f.png"))


@pytest.mark.parametrize(
    "n_refs,model,shape,ratio",
    [
        (0, "fal-ai/flux-pro/kontext/text-to-image", "v", "2:3"),
        (1, "fal-ai/flux-pro/kontext", "sq", "1:1"),
        (2, "fal-ai/flux-pro/kontext/max/multi", "l", "3:2"),
    ],
)
def test_fal_picks_the_model_by_refs_sends_data_uris_and_downloads(
    keys, monkeypatch, tmp_path, n_refs, model, shape, ratio
):
    refs = []
    for i in range(n_refs):
        refs.append(tmp_path / f"r{i}.png")
        refs[-1].write_bytes(picture())
    f = fake(monkeypatch, {"images": [{"url": "https://v3.fal.media/files/x.png"}]}, picture("JPEG"))
    FalWorker(1).generate(ImageJob("barn", tmp_path / "out.png", shape=shape, refs=refs))
    req, body = f.seen[0], f.json()
    assert req.full_url == f"https://fal.run/{model}" and req.get_header("Authorization") == "Key f-test"
    assert body["aspect_ratio"] == ratio and body["output_format"] == "png" and body["prompt"] == "barn"
    uris = [body["image_url"]] if n_refs == 1 else body.get("image_urls", [])
    assert len(uris) == n_refs and all(u.startswith("data:image/png;base64,") for u in uris)
    assert f.seen[1].full_url == "https://v3.fal.media/files/x.png" and f.seen[1].get_method() == "GET"
    assert is_png(tmp_path / "out.png")


def test_a_dead_key_is_a_fatal_one_line_error(keys, monkeypatch, tmp_path):
    body = io.BytesIO(
        json.dumps({"error": {"message": "Incorrect API key provided: sk-t***", "code": "invalid_api_key"}}).encode()
    )
    fake(monkeypatch, urllib.error.HTTPError("u", 401, "Unauthorized", {}, body))
    with pytest.raises(RuntimeError) as e:
        OpenAIWorker(1).generate(ImageJob("x", tmp_path / "f.png"))
    msg = str(e.value)
    assert msg.startswith("openai-1: http 401: invalid_api_key") and "\n" not in msg
    assert any(s in msg.lower() for s in FATAL)
    assert not (tmp_path / "f.png").exists()


def test_a_missing_key_stops_the_worker_before_any_request(monkeypatch):
    monkeypatch.setattr(catalog.secrets, "get", lambda name: None)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not set"):
        OpenAIWorker(1)


def test_check_lists_models_and_raises_on_a_bad_key(keys, monkeypatch):
    f = fake(monkeypatch, {"models": [{"name": "models/gemini-nano-banana-2.1"}]})
    assert check("gemini") == "Gemini key works"
    assert f.seen[0].get_method() == "GET" and f.seen[0].full_url.startswith(
        "https://generativelanguage.googleapis.com/v1beta/models"
    )
    fake(monkeypatch, {"prices": [{"endpoint_id": "fal-ai/flux-pro/kontext", "unit_price": 0.04, "unit": "image"}]})
    assert check("fal") == "fal key works"
    fake(
        monkeypatch, urllib.error.HTTPError("u", 401, "Unauthorized", {}, io.BytesIO(b'{"error": {"message": "bad"}}'))
    )
    with pytest.raises(RuntimeError, match="openai: http 401: bad"):
        check("openai")


def test_available_lists_public_providers_whose_key_is_set(monkeypatch):
    monkeypatch.setattr(catalog, "private", None)
    monkeypatch.setattr(catalog.secrets, "get", lambda name: "k" if name == "FAL_KEY" else None)
    assert available() == {"fal": 3}
    assert {p["id"] for p in catalog.PROVIDERS} == {"openai", "gemini", "fal"}
