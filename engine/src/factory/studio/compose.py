"""Scripts. The factory does not write them: the owner types one in the app, or an agent (Claude over MCP) writes it
from the owner's brief. Here: an empty script to fill in, the guide an agent writes by, and the checks every script
passes before it is saved."""

from __future__ import annotations

import copy
import re

from jsonschema import ValidationError, validate

from factory.core import LANGUAGES, formats
from factory.voice.text import PAUSE

WORDS_PER_SECOND = 2.3  # measured narration pace
CYRILLIC = re.compile(r"[а-яё]", re.I)  # note: the English check only catches Cyrillic, the languages that need it


def _mode(b: dict) -> tuple[dict, str]:
    """The script's format and render mode; ValueError when either is unknown."""
    fmt = formats.load(b.get("format"))
    mode = formats.mode(fmt, b)
    if mode not in fmt["render_modes"]:
        raise ValueError(f"format {fmt['id']} has no render mode {mode}; modes: {', '.join(fmt['render_modes'])}")
    return fmt, mode


def problems(b: dict) -> list[str]:
    """What the schema cannot say: numbers as words, English image prompts (fields marked english), voice length."""
    try:
        fmt, mode = _mode(b)
    except ValueError as e:
        return [f"schema: {e}"]
    out = []
    try:
        validate(b, formats.schema(fmt))
    except ValidationError as e:
        out.append(f"schema: {e.message} at {'/'.join(map(str, e.path))}")
    english = formats.keys(fmt, mode, "beat", "english")
    for i, beat in enumerate(b.get("beats", []), 1):
        if b.get("voice") and re.search(r"\d", PAUSE.sub("", beat.get("vo", ""))):
            out.append(f"beat {i}: vo has digits, write numbers as words")
        out += [f"beat {i}: {f} must be English" for f in english if CYRILLIC.search(str(beat.get(f, "")))]
        if b.get("voice") and beat.get("vo"):
            need = len(PAUSE.sub("", beat["vo"]).split()) / WORDS_PER_SECOND + 0.9
            if need > beat["seconds"] + 3:
                out.append(f"beat {i}: vo needs ~{need:.0f}s but seconds is {beat['seconds']}")
    out += [
        f"{f} must be English"
        for f in formats.keys(fmt, mode, "script", "english")
        if CYRILLIC.search(str(b.get(f, "")))
    ]
    return out


def missing(b: dict) -> list[str]:
    """Empty required fields of the script's render mode, which would make a broken video; generation waits until
    they are filled."""
    fmt, mode = _mode(b)
    out = [f for f in formats.keys(fmt, mode, "script", "required") if not str(b.get(f, "")).strip()]
    fields = formats.keys(fmt, mode, "beat", "required") + (["vo"] if b.get("voice") else [])
    for i, beat in enumerate(b.get("beats", []), 1):
        out += [f"beat {i} {f}" for f in fields if not str(beat.get(f, "")).strip()]
    return out


def blank(
    topic: str,
    duration: int,
    style: str,
    style_prompt: str | None,
    voice: bool,
    language: str,
    render_mode: str | None = None,
    format_id: str | None = None,
) -> dict:
    """A script with empty beats, about one per six seconds, for the owner to fill in: the format's `blank` skeleton
    plus the render mode's required fields, left empty."""
    fmt = formats.load(format_id)
    b = {"format": fmt["id"], "render_mode": render_mode or formats.mode(fmt, {})}
    fmt, mode = _mode(b)
    skel = fmt.get("blank") or {}
    n = max(4, min(12, round(duration / 6)))
    seconds = max(2, min(15, round(duration / n)))
    beat = {
        **skel.get("beat", {}),
        **dict.fromkeys(formats.keys(fmt, mode, "beat", "required"), ""),
        "seconds": seconds,
        **({"vo": ""} if voice else {}),
    }
    b |= {
        "language": language,
        "title": topic[:120],
        **dict.fromkeys(formats.keys(fmt, mode, "script", "required"), ""),
        **copy.deepcopy(skel.get("script", {})),
        "style": style,
        "voice": voice,
        "beats": [copy.deepcopy(beat) for _ in range(n)],
    }
    if style_prompt:
        b["style_prompt"] = style_prompt
    return b


def guide(language: str = "en", format_id: str | None = None) -> str:
    """Everything an agent needs to write a valid script in one read: the format's guide.md with the engine's
    generic facts filled in, and its finished example."""
    fmt = formats.load(format_id)
    values = {
        "languages": ", ".join(LANGUAGES),
        "language_name": LANGUAGES.get(language, language),
        "words_per_second": str(WORDS_PER_SECOND),
        "schema": f"formats/{fmt['id']}/beats.schema.json",
    }
    text = (fmt["dir"] / "guide.md").read_text(encoding="utf-8").strip()
    for k, v in values.items():
        text = text.replace("{" + k + "}", v)
    example = next(iter(formats.examples(fmt)), None)
    return text + ("\n\nExample of a finished episode:\n" + example.read_text(encoding="utf-8") if example else "")
