"""Whisper on MLX (Apple Silicon) with word timestamps."""

from __future__ import annotations

from pathlib import Path


def words(wav: Path, language: str, model: str) -> list[dict]:
    import mlx_whisper

    res = mlx_whisper.transcribe(  # pyright: ignore[reportAttributeAccessIssue]  exported lazily
        str(wav), path_or_hf_repo=model, language=language, word_timestamps=True, condition_on_previous_text=False
    )
    segments: list[dict] = res["segments"]  # type: ignore[assignment]
    return [{"word": w["word"], "start": w["start"], "end": w["end"]} for seg in segments for w in seg.get("words", [])]
