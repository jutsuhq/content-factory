"""Voice studio: say any phrase the way the pipeline would."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from factory.api.paths import SAMPLES
from factory.core import LANGUAGES, load_profile, voice_for
from factory.core.profile import DEFAULT_VOICES
from factory.stages.tts import synthesize
from factory.voice import text

router = APIRouter()


@router.get("/voices")
def voices() -> dict:
    """Languages an episode can be voiced (and translated) in, with the voice each one uses."""
    profile = load_profile()
    return {
        code: {"name": LANGUAGES[code], **voice_for(profile, code)}
        for code in LANGUAGES
        if code in profile["voices"] or code in DEFAULT_VOICES
    }


class SayIn(BaseModel):
    text: str
    language: str = "en"


@router.post("/voice/say")
def say(body: SayIn) -> dict:
    """The line through the same path as a beat: markup, numbers, pauses, trimming."""
    line = text.prepare(body.text, body.language)
    name = f"{uuid.uuid4().hex[:10]}.wav"
    synthesize(line, voice_for(load_profile(), body.language), SAMPLES / name)
    return {"spoken": text.display(line), "audio": f"samples/{name}"}
