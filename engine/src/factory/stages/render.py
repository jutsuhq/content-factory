"""render: write timeline.json from the beats and stage outputs, render it with the format's Remotion composition
(format.yaml `template`), lay the episode's music under it (music.library picks the track, ducked under the voice),
then bring the audio to the loudness short-video apps play at."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from factory import stages
from factory.core import DATA, ROOT, Episode, formats
from factory.music import library
from factory.stages.transitions import FRAMES_PER_PAIR
from factory.voice import audio, fit

FPS = 30
MORPH_SECONDS = 1.5

# The Remotion project. In a checkout it is render/ itself; the app's resources are read-only, so it copies render/ to
# DATA, where npm can install into it. Either way the template comes from the episode's format (gather_template).
RENDER = ROOT / "render" if DATA == ROOT / "data" else DATA / "render"
TEMPLATES = DATA / "render-formats"  # the template an episode renders with, gathered for its bundle


def gather_template(ep: Episode) -> Path:
    """Copy the episode's format's template/ into TEMPLATES/<slug>/<id>/template/, the one folder the renderer
    bundles (CF_FORMATS). Only this format's: shipped and own formats live in two places, and a copy of a format may
    keep its composition id, which must be unique in a bundle."""
    out = TEMPLATES / ep.slug
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(ep.format_dir / "template", out / ep.format_dir.name / "template")
    return out


def timeline(ep: Episode) -> dict:
    """The template's props: the style preset's `props`, the script's own fields (top level and per beat, the spoken
    line aside), timing from the voice, and the files of whichever picture stages the render mode runs."""
    pub = ep.work()
    beats, t = [], 0.0
    src = ep.beats["beats"]
    runs = set(stages.plan(ep))
    for i, beat in enumerate(src, 1):
        n = f"{i:02d}"
        voice = pub / "voice" / f"{n}.wav"
        words = pub / "voice" / f"{n}.words.json"
        has_voice = ep.beats.get("voice") and voice.exists()
        length = fit.beat_length(beat["seconds"], audio.duration(voice) if has_voice else None)
        item = {
            **{k: v for k, v in beat.items() if k not in ("vo", "seconds")},
            "start": round(t, 3),
            "duration": round(length, 3),
            **({"image": f"frames/{n}-916.png"} if "frames" in runs else {}),
            **({"depth": f"frames/{n}-916-depth.png"} if "depth" in runs else {}),
            "voice": f"voice/{n}.wav" if has_voice else None,
            "words": json.loads(words.read_text(encoding="utf-8")) if has_voice and words.exists() else [],
        }
        if i < len(src) and "transitions" in runs:
            item["morph"] = {"dir": f"rife/{n}-{i + 1:02d}", "count": FRAMES_PER_PAIR, "seconds": MORPH_SECONDS}
        beats.append(item)
        t += length
    top = {k: v for k, v in ep.beats.items() if k != "beats"}
    props = formats.styles(ep.format["id"]).get(ep.beats.get("style"), {}).get("props", {})  # the preset's, if any
    return {
        **props,
        **top,
        "mode": formats.mode(ep.format, ep.beats),
        "fps": FPS,
        "duration": round(t, 3),
        "beats": beats,
    }


def run(ep: Episode, profile: dict) -> None:
    tl = timeline(ep)
    props = ep.work() / "timeline.json"
    props.write_text(json.dumps({"timeline": tl}, ensure_ascii=False, indent=1), encoding="utf-8")
    out = ep.dir / "out" / f"{ep.slug}.mp4"
    out.parent.mkdir(exist_ok=True)
    raw = out.with_name(f"{ep.slug}.raw.mp4")
    npx = shutil.which("npx") or "npx"  # npx.cmd on Windows
    templates = gather_template(ep)
    subprocess.run(
        [
            npx,
            "remotion",
            "render",
            "src/index.ts",
            ep.format["template"],
            str(raw),
            f"--props={props}",
            f"--public-dir={ep.work()}",
            "--gl=angle",
            "--timeout=120000",
            "--log=error",
        ],
        cwd=RENDER,
        env={**os.environ, "CF_FORMATS": str(templates)},
        check=True,
    )
    shutil.rmtree(templates, ignore_errors=True)
    mood = " ".join(
        str(ep.beats.get(k, ""))
        for k in ("title", *formats.keys(ep.format, tl["mode"], "script", "translate"), "style")
    )
    track = library.pick(ep.beats.get("music"), mood)
    mixed = raw
    if track:
        mixed = out.with_name(f"{ep.slug}.mix.mp4")
        audio.mix_music(raw, library.DIR / track["file"], mixed, tl["duration"])
    level = audio.loudness(mixed, out)
    for tmp in {raw, mixed}:
        tmp.unlink()
    (ep.dir / "out" / "music.json").write_text(json.dumps(track, ensure_ascii=False), encoding="utf-8")
    print(
        f"render: {out} ({tl['duration']:.1f}s, music {track['id'] if track else 'none'}, "
        f"{level['before']:.1f} -> {level['after']:.0f} LUFS)"
    )
