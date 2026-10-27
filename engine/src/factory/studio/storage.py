"""Disk use of the episodes folder, the cache that is safe to drop, the trash, and copying accepted videos out."""

from __future__ import annotations

import shutil
from pathlib import Path

from factory.core import EPISODES, storage
from factory.studio import store

# Rebuilt by the transitions stage on the next rebuild, a few minutes of local work. Frames are not here: they come
# from the image subscription and take the longest to make again.
CACHE = ("work/public/rife",)
SETTLED = ("review", "done", "failed")


def _size(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.exists() else 0


def trash() -> Path:
    return EPISODES / ".trash"


def usage() -> dict:
    """Bytes per kind; `cache` only counts episodes that are not being generated."""
    videos = frames = cache = other = 0
    for d in EPISODES.iterdir() if EPISODES.exists() else []:
        if not d.is_dir() or d.name.startswith("."):
            continue
        total = _size(d)
        v, f = _size(d / "out"), _size(d / "work" / "public" / "frames")
        c = sum(_size(d / c) for c in CACHE)
        settled = store.meta(d.name).get("status") in SETTLED
        videos, frames = videos + v, frames + f
        cache += c if settled else 0
        other += total - v - f - (c if settled else 0)
    free = shutil.disk_usage(EPISODES if EPISODES.exists() else Path.home()).free
    return {"videos": videos, "frames": frames, "cache": cache, "other": other, "trash": _size(trash()), "free": free}


def clear_cache(slug: str | None = None) -> int:
    """Drops the cache of settled episodes (or one episode); answers the bytes freed."""
    freed = 0
    dirs = [EPISODES / slug] if slug else [d for d in EPISODES.iterdir() if d.is_dir() and not d.name.startswith(".")]
    for d in dirs:
        if store.meta(d.name).get("status") not in SETTLED:
            continue
        for c in CACHE:
            freed += _size(d / c)
            shutil.rmtree(d / c, ignore_errors=True)
    return freed


def empty_trash() -> int:
    freed = _size(trash())
    shutil.rmtree(trash(), ignore_errors=True)
    return freed


def export(slug: str) -> Path:
    """Copies the finished video to the export folder under its title; never over an existing file."""
    src = EPISODES / slug / "out" / f"{slug}.mp4"
    folder = Path(storage()["export_dir"]).expanduser()
    folder.mkdir(parents=True, exist_ok=True)
    name = store.slugify(store.meta(slug).get("title") or slug) or slug
    out, n = folder / f"{name}.mp4", 2
    while out.exists():
        out, n = folder / f"{name}-{n}.mp4", n + 1
    shutil.copy2(src, out)
    return out
