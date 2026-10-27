"""Speech to text with word timings. A backend module has `words(wav, language, model) -> [{word, start, end}]`.
faster-whisper (Windows / NVIDIA) is still to add here, see docs/platforms.md."""

from __future__ import annotations

from pathlib import Path

from factory.providers.stt import mlx_whisper

BACKENDS = {"mlx-whisper": mlx_whisper}


def words(provider: str, wav: Path, language: str, model: str) -> list[dict]:
    if provider not in BACKENDS:
        raise SystemExit(f"stt provider {provider} is not implemented yet")
    return BACKENDS[provider].words(wav, language, model)
