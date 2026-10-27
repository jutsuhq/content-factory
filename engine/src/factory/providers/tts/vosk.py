"""Vosk-TTS (VITS, Apache-2.0): Russian on CPU on every OS. It reads `+` stress marks, so RUAccent places them first;
a word the line already marks (`з+амок`) keeps its own stress."""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

LANGUAGES = {"ru"}
_MARKED_WORD = re.compile(r"\w*\+\w+")


@cache
def _accentizer():
    from ruaccent import RUAccent

    acc = RUAccent()
    acc.load(omograph_model_size="turbo3.1", use_dictionary=True)
    return acc


def mark(text: str) -> str:
    own = {w.replace("+", "").lower(): w for w in _MARKED_WORD.findall(text)}
    marked = _accentizer().process_all(text.replace("+", ""))
    return re.sub(r"[\w+]+", lambda m: own.get(m.group(0).replace("+", "").lower(), m.group(0)), marked)


def load(voice: dict):
    try:
        from vosk_tts import Model, Synth
    except ImportError:
        raise SystemExit(
            "the Russian voice is not installed: Settings › Components, or `uv sync --extra vosk`"
        ) from None

    synth = Synth(Model(model_name=voice["model"]))

    def say(text: str, out: Path) -> None:
        synth.synth(mark(text), str(out), speaker_id=int(voice["speaker"]))

    return say
