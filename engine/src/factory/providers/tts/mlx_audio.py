"""MLX-Audio on Apple Silicon: Kokoro and the other models it runs."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

LANGUAGES = {"en", "ru", "es", "fr", "it", "pt", "ja", "zh", "hi"}


def _short_espeak_path() -> None:
    """espeak-ng keeps its data path in a fixed-size buffer and quietly falls back to its build machine's path when
    the real one is longer, which a deeply nested checkout reaches. Point it at a short copy instead: a symlink
    would not help, phonemizer resolves it back to the long path."""
    try:
        import espeakng_loader
        import misaki.espeak  # noqa: F401  sets the long path on import, so it has to come first
        from phonemizer.backend.espeak.wrapper import EspeakWrapper
    except ImportError:
        return
    real = Path(espeakng_loader.get_data_path())
    if len(str(real)) < 100:
        return
    short = Path(tempfile.gettempdir()) / "content-factory-espeak-data"
    if not (short / "phontab").exists():
        shutil.copytree(real, short, dirs_exist_ok=True)
    EspeakWrapper.set_data_path(str(short))


def load(voice: dict):
    from mlx_audio.tts.generate import generate_audio
    from mlx_audio.tts.utils import load_model

    _short_espeak_path()
    model = load_model(voice["model"])

    def say(text: str, out: Path) -> None:
        generate_audio(
            text=text,
            model=model,
            voice=voice["speaker"],
            lang_code=voice.get("lang_code", "a"),
            speed=float(voice.get("speed", 1.0)),
            output_path=str(out.parent),
            file_prefix=out.stem,
            join_audio=True,
            verbose=False,
        )

    return say
