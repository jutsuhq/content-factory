"""Episodes: start one with a script (or an empty one), edit and approve it, generate, review, redo one frame,
make another-language copy, accept, and hand the video to the desktop (Finder, player, clipboard)."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from factory import jobs, stages
from factory.core import EPISODES, LANGUAGES, defaults, desktop, formats, storage
from factory.studio import compose, store, translate
from factory.studio import storage as disk

router = APIRouter()


def _require(slug: str) -> Path:
    d = EPISODES / slug
    if "/" in slug or ".." in slug or not d.is_dir():
        raise HTTPException(404, "no such episode")
    return d


class ComposeIn(BaseModel):
    topic: str
    duration: int | None = None  # None: the owner's default from Settings, like style, voice and language
    style: str | None = None
    style_prompt: str | None = None
    voice: bool | None = None
    language: str | None = None
    series: str | None = None  # continue this series
    script: dict | None = None  # a finished beats.json (an agent wrote it); without it the script starts empty
    format: str | None = None  # None: the script's own, else the owner's default
    render_mode: str | None = None  # for an empty script: one of the format's render modes, None for its first


@router.post("/compose")
def compose_episode(body: ComposeIn) -> dict:
    """A new episode waiting at the script step: the given script, or an empty one to fill in."""
    if not body.topic.strip() or len(body.topic) > 2000:
        raise HTTPException(400, "topic must be 1-2000 characters")
    d = defaults()
    language = (body.script or {}).get("language") or body.language or d["language"]
    if language not in LANGUAGES:
        raise HTTPException(400, f"language must be one of {', '.join(LANGUAGES)}")
    try:
        fmt = formats.load(body.format or (body.script or {}).get("format"))
        mode = body.render_mode or (body.script or {}).get("render_mode") or formats.mode(fmt, {})
        known = formats.style_ids(fmt, mode)
    except (ValueError, KeyError):
        raise HTTPException(400, f"unknown format or render mode; formats: {', '.join(formats.ids())}") from None
    duration = body.duration or d["duration"]
    # the owner's default style is a preset of the default format; anything else starts with the mode's first style
    style = (
        body.style or (body.script or {}).get("style") or (d["style"] if d["style"] in known else next(iter(known), ""))
    )
    voice = d["voice"] if body.voice is None else body.voice
    if body.script:
        script = {
            **body.script,
            "format": fmt["id"],
            "render_mode": mode,
            "language": language,
            "style": style,
            "voice": bool(body.script.get("voice", voice)),
        }
        if body.style_prompt:
            script["style_prompt"] = body.style_prompt
    else:
        try:
            script = compose.blank(body.topic, duration, style, body.style_prompt, voice, language, mode, fmt["id"])
        except ValueError as e:
            raise HTTPException(400, str(e)) from None
    issues = compose.problems(script)
    if any(i.startswith("schema") for i in issues):
        raise HTTPException(400, "; ".join(issues))
    slug = store.new_slug((script.get("title") or body.topic)[:60])
    index = 1
    if body.series:
        index = 1 + max(
            (
                e.get("episode_index", 1)
                for e in store.list_episodes()
                if e.get("series") == body.series and not e.get("translation_of")
            ),
            default=0,
        )
    store.write_json(EPISODES / slug / "beats.json", script)
    store.save_meta(
        slug,
        status="script",
        topic=body.topic,
        title=script.get("title") or body.topic[:80],
        series=body.series or slug,
        episode_index=index,
        duration=duration,
        language=language,
        created=time.time(),
    )
    return {"slug": slug, "warnings": [i for i in issues if not i.startswith("schema")]}


@router.get("/episodes")
def episodes() -> list[dict]:
    return store.list_episodes()


@router.get("/episodes/{slug}")
def episode(slug: str) -> dict:
    _require(slug)
    return store.episode_view(slug)


@router.put("/episodes/{slug}/beats")
def save_beats(slug: str, beats: dict) -> dict:
    _require(slug)
    issues = compose.problems(beats)
    if any(i.startswith("schema") for i in issues):
        raise HTTPException(400, "; ".join(issues))
    store.write_json(EPISODES / slug / "beats.json", beats)
    store.save_meta(slug, title=beats.get("title") or store.meta(slug).get("title"))
    return {"warnings": issues}


@router.post("/episodes/{slug}/approve")
def approve(slug: str) -> dict:
    _require(slug)
    empty = compose.missing(store.beats(slug) or {})
    if empty:
        raise HTTPException(
            400, "fill in before generating: " + ", ".join(empty[:12]) + (" …" if len(empty) > 12 else "")
        )
    store.save_meta(slug, status="approved", error=None)
    return {"job": jobs.submit("generate", slug)}


@router.post("/episodes/{slug}/rerun")
def rerun(slug: str, names: list[str] | None = None) -> dict:
    _require(slug)
    store.save_meta(slug, status="approved")
    return {"job": jobs.submit("stages", slug, stages=names or stages.ORDER)}


@router.post("/episodes/{slug}/beats/{n}/regenerate")
def regenerate_beat(slug: str, n: int) -> dict:
    """New variant of one frame: drop its cache key, then the cached pipeline redoes only what depends on it."""
    d = _require(slug)
    frames = d / "work" / "public" / "frames"
    (frames / f"{n:02d}.png.key").unlink(missing_ok=True)
    if n == 1:  # every other frame is an edit of the first one
        for k in frames.glob("*.png.key"):
            k.unlink()
    store.save_meta(slug, status="approved")
    return {"job": jobs.submit("stages", slug, stages=stages.ORDER, beat=n)}


class TranslateIn(BaseModel):
    language: str
    texts: dict | None = None  # translated {title, hook, cta, objection?, beats: [{counter, caption, vo}]}


@router.post("/episodes/{slug}/translate")
def translate_episode(slug: str, body: TranslateIn) -> dict:
    """A version in another language that reuses this episode's frames; it opens as a script to approve."""
    _require(slug)
    try:
        return {"slug": translate.translate(slug, body.language, body.texts)}
    except ValueError as e:
        raise HTTPException(400, str(e)) from None


class AcceptIn(BaseModel):
    caption: str = ""


@router.post("/episodes/{slug}/accept")
def accept(slug: str, body: AcceptIn) -> dict:
    """Marks the video done and keeps its caption; posting it anywhere is up to the owner. With the storage settings
    on, the video is copied to the export folder (once) and the episode's cache is dropped."""
    d = _require(slug)
    video = d / "out" / f"{slug}.mp4"
    m = store.save_meta(slug, status="done", caption=body.caption)
    s = storage()
    if s["copy_on_accept"] and video.exists() and not m.get("exported"):
        m = store.save_meta(slug, exported=str(disk.export(slug)))
    if s["clean_after_accept"]:
        disk.clear_cache(slug)
    return {"video": str(video), "exported": m.get("exported")}


DESKTOP = {"reveal": desktop.reveal, "open": desktop.open_file, "copy": desktop.copy_file}


@router.post("/episodes/{slug}/video/{action}")
def video_action(slug: str, action: Literal["reveal", "open", "copy"]) -> dict:
    """Show the finished video in Finder or Explorer, open it in the player, or copy the file to the clipboard."""
    video = _require(slug) / "out" / f"{slug}.mp4"
    if not video.exists():
        raise HTTPException(404, "no video yet")
    try:
        DESKTOP[action](video)
    except (RuntimeError, OSError, subprocess.CalledProcessError) as e:
        raise HTTPException(400, str(e)) from None
    return {"ok": True}


@router.delete("/episodes/{slug}")
def remove(slug: str) -> dict:
    """Moves the episode to episodes/.trash, nothing is deleted."""
    d = _require(slug)
    trash = EPISODES / ".trash"
    trash.mkdir(exist_ok=True)
    d.rename(trash / f"{slug}-{int(time.time())}")
    return {"ok": True}
