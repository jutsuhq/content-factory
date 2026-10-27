"""Text to speech. A backend module has `LANGUAGES` and `load(voice) -> say(text, out_wav)`. A voice is one entry of
`voices` in profile.yaml, e.g. `{engine: mlx-audio, model: mlx-community/Kokoro-82M-bf16, speaker: af_heart}`.
Add an engine: a module plus a line in ENGINES."""

from __future__ import annotations

import json
from functools import cache
from types import ModuleType

from factory.providers.tts import mlx_audio, vosk

ENGINES: dict[str, ModuleType] = {"vosk": vosk, "mlx-audio": mlx_audio}


def engine(voice: dict) -> ModuleType:
    name = voice.get("engine", "mlx-audio")
    if name not in ENGINES:
        raise SystemExit(f"tts engine {name} is not installed; known: {', '.join(ENGINES)}")
    return ENGINES[name]


@cache
def _load(voice_json: str):
    voice = json.loads(voice_json)
    return engine(voice).load(voice)


def speaker(voice: dict):
    """`say(text, out_wav)` for this voice; the model loads once per process."""
    return _load(json.dumps(voice, sort_keys=True))
