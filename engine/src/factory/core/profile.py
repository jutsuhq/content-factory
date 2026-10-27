"""profile.yaml: what `factory doctor` found on this machine and which provider runs each stage.

Voices are per language (`voices: {en: {...}, ru: {...}}`): each language may need its own engine.
"""

from __future__ import annotations

import platform
from pathlib import Path

import yaml

from factory.core.paths import PROFILE

# Used when the profile has no voice for a language.
DEFAULT_VOICES = {
    "en": {"engine": "mlx-audio", "model": "mlx-community/Kokoro-82M-bf16", "speaker": "af_heart", "lang_code": "a"},
    "ru": {"engine": "vosk", "model": "vosk-model-tts-ru-0.9-multi", "speaker": 0},
}


def load_profile() -> dict:
    if not PROFILE.exists():
        raise SystemExit("profile.yaml not found: run `factory doctor` first")
    profile = yaml.safe_load(PROFILE.read_text(encoding="utf-8"))
    profile.setdefault("voices", dict(DEFAULT_VOICES))
    return profile


# What a new video starts with; the owner changes them in Settings (profile.yaml `defaults`). An unset or missing
# format is the first one found, an unset style that format's first style.
DEFAULTS = {"language": "en", "format": None, "style": None, "duration": 60, "voice": True}


def defaults() -> dict:
    from factory.core import formats

    saved = (load_profile().get("defaults") or {}) if PROFILE.exists() else {}
    out = {**DEFAULTS, **{k: v for k, v in saved.items() if k in DEFAULTS}}
    found = formats.ids()
    if out["format"] not in found:
        out["format"] = found[0] if found else None
    if out["format"] and out["style"] not in formats.styles(out["format"]):  # unset, or a style of another format
        out["style"] = next(iter(formats.styles(out["format"])), None)
    return out


def save_profile(profile: dict) -> None:
    PROFILE.write_text(yaml.safe_dump(profile, sort_keys=False, allow_unicode=True), encoding="utf-8")


def voice_for(profile: dict, language: str) -> dict:
    voice = profile["voices"].get(language) or DEFAULT_VOICES.get(language)
    if not voice:
        raise SystemExit(f"no voice for language {language}: add one under `voices` in profile.yaml")
    return voice


# Where accepted videos are copied and what happens to the transition cache; Settings › Storage (profile `storage`).
STORAGE = {
    "export_dir": str(Path.home() / ("Movies" if platform.system() == "Darwin" else "Videos") / "Content Factory"),
    "copy_on_accept": True,
    "clean_after_accept": False,
}


def storage() -> dict:
    saved = (load_profile().get("storage") or {}) if PROFILE.exists() else {}
    return {**STORAGE, **{k: v for k, v in saved.items() if k in STORAGE}}
