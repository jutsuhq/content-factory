"""Episodes on disk: episodes/<slug>/ holds beats.json (the script), meta.json (status, series, settings)
and refs/ (images the owner attached). Series are episodes that share a `series` id."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from factory.core import DATA, EPISODES, FORMATS, formats

# draft: being written by Claude; script: waits for the owner's approval; approved: queued or generating;
# review: video ready, waits for acceptance; done: accepted; failed: a stage broke.
STATUSES = ("draft", "script", "approved", "generating", "review", "done", "failed")


def slugify(text: str) -> str:
    table = str.maketrans("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", "abvgdeejziiklmnoprstufhccss_y_eua")
    s = re.sub(r"[^a-z0-9]+", "-", text.lower().translate(table)).strip("-")
    return s[:40] or "episode"


def new_slug(title: str) -> str:
    base = f"{time.strftime('%Y-%m-%d')}-{slugify(title)}"
    slug, n = base, 2
    while (EPISODES / slug).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


def read_json(p: Path, default=None):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def meta(slug: str) -> dict:
    return read_json(EPISODES / slug / "meta.json", {"slug": slug, "status": "script"}) or {}


def save_meta(slug: str, **changes) -> dict:
    m = {**meta(slug), **changes, "slug": slug, "updated": time.time()}
    write_json(EPISODES / slug / "meta.json", m)
    return m


def beats(slug: str) -> dict | None:
    return read_json(EPISODES / slug / "beats.json")


def episode_view(slug: str) -> dict:
    """Everything the app shows for one episode."""
    d = EPISODES / slug
    pub = d / "work" / "public"
    b = beats(slug)
    m = meta(slug)
    video = d / "out" / f"{slug}.mp4"
    frames = sorted(p.name for p in (pub / "frames").glob("[0-9][0-9]-916.png")) if (pub / "frames").exists() else []
    return {
        **m,
        "title": (b or {}).get("title") or m.get("title") or slug,
        "beats": b,
        "frames": frames,
        "video": f"out/{slug}.mp4" if video.exists() else None,
        "video_mtime": video.stat().st_mtime if video.exists() else None,
        "thumb": f"work/public/frames/{frames[0]}" if frames else None,
    }


def list_episodes() -> list[dict]:
    out = []
    for d in EPISODES.iterdir() if EPISODES.exists() else []:
        if (d / "beats.json").exists() or (d / "meta.json").exists():
            out.append(episode_view(d.name))
    return sorted(out, key=lambda e: e.get("updated") or e.get("created") or 0, reverse=True)


def preview_path(format_id: str, sid: str) -> Path:
    """Where a generated style preview is written: in DATA, so the shipped ones stay untouched."""
    return DATA / "formats" / format_id / "previews" / f"{sid}.png"


def preview_url(format_id: str, sid: str) -> str | None:
    """Path under the engine's /files/: a generated preview wins over the shipped one."""
    if preview_path(format_id, sid).exists():
        return f"data-formats/{format_id}/previews/{sid}.png"
    shipped = FORMATS / format_id / "previews" / f"{sid}.png"
    return f"formats/{format_id}/previews/{sid}.png" if shipped.exists() else None


def styles(format_id: str | None = None) -> list[dict]:
    """A format's style presets (the default format for None), each with its preview."""
    fid = format_id or formats.default_id()
    return [{"id": sid, **s, "preview": preview_url(fid, sid)} for sid, s in formats.styles(fid).items()]
