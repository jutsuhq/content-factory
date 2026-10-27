"""Pipeline stages, in order. A stage is a module with `run(episode, profile)` that reads what earlier stages left in
work/public, skips every output whose inputs did not change (core.cache), and prints one line per thing it made (the
job queue parses those lines for progress). Which stages an episode runs is declared by its format's render mode
(format.yaml `render_modes.<mode>.stages`); the voice stages run only for a narrated script."""

from __future__ import annotations

import importlib

from factory.core import Episode, formats

ORDER = ["frames", "depth", "transitions", "tts", "align", "render", "qa"]
VOICE = {"tts", "align"}  # they work on the `vo` lines, which only a script with voice: true has


def plan(ep: Episode, names: list[str] | None = None) -> list[str]:
    """The stages this episode runs, in ORDER: its render mode's, narrowed to `names` when given."""
    for name in names or []:
        if name not in ORDER:
            raise SystemExit(f"unknown stage {name}; stages: {', '.join(ORDER)}")
    fmt = ep.format
    declared = fmt["render_modes"][formats.mode(fmt, ep.beats)]["stages"]
    return [
        n for n in ORDER if n in declared and (not names or n in names) and (ep.beats.get("voice") or n not in VOICE)
    ]


def run(ep: Episode, profile: dict, names: list[str] | None = None) -> None:
    for name in plan(ep, names):
        importlib.import_module(f"factory.stages.{name}").run(ep, profile)
