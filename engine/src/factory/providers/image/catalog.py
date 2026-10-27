"""What the app shows about image providers: the public APIs with key, sign-up link and default parallelism, which of
them (plus optional local workers) can run on this machine, and a free key check."""

from __future__ import annotations

from factory.core import secrets
from factory.providers.image import fal, gemini, openai
from factory.providers.image.pool import private

PROVIDERS = [
    {
        "id": "openai",
        "title": "OpenAI GPT Image",
        "key": openai.KEY,
        "signup": "https://platform.openai.com/api-keys",
        "workers": 2,
        "edits": True,
        "note": f"{openai.MODEL}, {openai.QUALITY} quality. "
        "An organization may need to be verified before image models work.",
    },
    {
        "id": "gemini",
        "title": "Google Gemini (Nano Banana)",
        "key": gemini.KEY,
        "signup": "https://aistudio.google.com/apikey",
        "workers": 3,
        "edits": True,
        "note": f"{gemini.MODEL} at 1K resolution.",
    },
    {
        "id": "fal",
        "title": "fal.ai FLUX.1 Kontext",
        "key": fal.KEY,
        "signup": "https://fal.ai/dashboard/keys",
        "workers": 3,
        "edits": True,
        "note": "Kontext [pro] for text and one-reference edits, Kontext [max] multi for several references.",
    },
]
CHECKS = {"openai": openai.check, "gemini": gemini.check, "fal": fal.check}


def available() -> dict[str, int]:
    """{provider id: workers} for every provider that can run here: a public one with its key set, a local one
    when it says it works here."""
    found = {p["id"]: p["workers"] for p in PROVIDERS if secrets.get(p["key"])}
    return found | (private.available() if private else {})


def check(provider_id: str) -> str:
    """Validates a provider's key without generating anything; a short message, or RuntimeError on a bad key."""
    if provider_id not in CHECKS:
        raise RuntimeError(f"unknown image provider: {provider_id}")
    try:
        return CHECKS[provider_id]()
    except RuntimeError as e:
        raise RuntimeError(f"{provider_id}: {e}") from None
