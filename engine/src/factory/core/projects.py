"""Projects: one per channel (a TikTok or YouTube account), the space its videos are made in so they stay consistent.

projects/<id>/project.json holds the channel (name, platform, handle, color, a brief for agents), its variants and
its cast. A variant is a ready set of settings for one kind of video on the channel: format, render mode, style,
language, voice, length, the characters it uses and the post's hashtags. The cast is the channel's recurring
characters: a name, a looks text that goes into every frame prompt, and reference images in projects/<id>/cast/<cid>/.
"""

from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

from factory.core import formats
from factory.core.paths import PROJECTS
from factory.core.profile import defaults

PLATFORMS = ("tiktok", "youtube", "instagram", "other")
IMAGES = (".png", ".jpg", ".jpeg", ".webp")
REFS_PER_CHARACTER = 3  # references sent with a frame for each character, the first ones in the folder
# what a variant may set; unset keys fall back to the owner's defaults from Settings
VARIANT_KEYS = ("format", "render_mode", "style", "style_prompt", "language", "voice", "duration", "cast", "hashtags")


def _id(text: str, taken: set[str], fallback: str) -> str:
    table = str.maketrans("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", "abvgdeejziiklmnoprstufhccss_y_eua")
    base = re.sub(r"[^a-z0-9]+", "-", text.lower().translate(table)).strip("-")[:40] or fallback
    out, n = base, 2
    while out in taken:
        out, n = f"{base}-{n}", n + 1
    return out


def _dir(pid: str) -> Path:
    d = PROJECTS / pid
    if not pid or "/" in pid or ".." in pid or not (d / "project.json").exists():
        raise KeyError(pid)
    return d


def _read(pid: str) -> dict:
    return json.loads((_dir(pid) / "project.json").read_text(encoding="utf-8"))


def _write(p: dict) -> None:
    f = PROJECTS / p["id"] / "project.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(f)


def refs(pid: str, cid: str) -> list[Path]:
    d = PROJECTS / pid / "cast" / cid
    return sorted(f for f in d.iterdir() if f.suffix.lower() in IMAGES) if d.is_dir() else []


def load(pid: str) -> dict:
    """The project with each character's reference images, as paths under the engine's /files/."""
    p = _read(pid)
    for c in p["cast"]:
        c["refs"] = [f"projects/{pid}/cast/{c['id']}/{f.name}" for f in refs(pid, c["id"])]
    return p


def all_projects() -> list[dict]:
    found = [d.name for d in PROJECTS.iterdir() if (d / "project.json").exists()] if PROJECTS.exists() else []
    return sorted(map(load, found), key=lambda p: p.get("created", 0))


def _clean(p: dict, old: dict | None = None) -> dict:
    """A project as the owner sent it, checked: names set, ids unique, variants only with known settings."""
    name = str(p.get("name", "")).strip()
    if not name:
        raise ValueError("the project needs a name")
    cast, cids = [], set()
    for c in p.get("cast") or []:
        cname = str(c.get("name", "")).strip()
        if not cname:
            raise ValueError("every character needs a name")
        cid = c.get("id") if c.get("id") and c["id"] not in cids and "/" not in c["id"] else _id(cname, cids, "c")
        cids.add(cid)
        cast.append({"id": cid, "name": cname, "looks": str(c.get("looks", "")).strip()})
    variants, vids = [], set()
    for v in p.get("variants") or []:
        vname = str(v.get("name", "")).strip() or "Main"
        vid = v.get("id") if v.get("id") and v["id"] not in vids else _id(vname, vids, "v")
        vids.add(vid)
        given = {k: v[k].strip() if isinstance(v[k], str) else v[k] for k in VARIANT_KEYS if k in v}
        out = {"id": vid, "name": vname, **{k: x for k, x in given.items() if x not in (None, "")}}
        if out.get("format") and out["format"] not in formats.ids():
            raise ValueError(f"variant {vname}: unknown format {out['format']}")
        out["cast"] = [c for c in out.get("cast", []) if c in cids]
        variants.append(out)
    if not variants:
        raise ValueError("the project needs at least one variant")
    platform = p.get("platform") if p.get("platform") in PLATFORMS else "other"
    return {
        "id": (old or p)["id"],
        "name": name,
        "platform": platform,
        "handle": str(p.get("handle", "")).strip(),
        "color": str(p.get("color", "")).strip() or "#e8a33d",
        "brief": str(p.get("brief", "")).strip(),
        "variants": variants,
        "cast": cast,
        "created": (old or p).get("created") or time.time(),
    }


def create(p: dict) -> dict:
    """A new project; without variants it gets one, Main, with the owner's defaults."""
    PROJECTS.mkdir(parents=True, exist_ok=True)
    taken = {d.name for d in PROJECTS.iterdir()}
    d = defaults()
    first = {"name": "Main", **{k: d[k] for k in ("format", "style", "language", "voice", "duration")}}
    p = {**p, "id": _id(str(p.get("name", "")), taken, "project"), "variants": p.get("variants") or [first]}
    p = _clean(p)
    _write(p)
    return load(p["id"])


def save(pid: str, p: dict) -> dict:
    """Replace the project; a character dropped from the cast takes its reference images with it."""
    old = _read(pid)
    p = _clean(p, old)
    for c in old["cast"]:
        if c["id"] not in {n["id"] for n in p["cast"]}:
            shutil.rmtree(PROJECTS / pid / "cast" / c["id"], ignore_errors=True)
    _write(p)
    return load(pid)


def remove(pid: str, trash: Path) -> None:
    """Moves the project to trash; its videos stay where they are."""
    trash.mkdir(parents=True, exist_ok=True)
    _dir(pid).rename(trash / f"project-{pid}-{int(time.time())}")


def add_ref(pid: str, cid: str, name: str, data: bytes) -> dict:
    if cid not in {c["id"] for c in _read(pid)["cast"]}:
        raise KeyError(cid)
    ext = Path(name).suffix.lower()
    if ext not in IMAGES:
        raise ValueError(f"a reference is an image: {', '.join(IMAGES)}")
    d = PROJECTS / pid / "cast" / cid
    d.mkdir(parents=True, exist_ok=True)
    n = 1 + max((int(f.stem) for f in d.iterdir() if f.stem.isdigit()), default=0)
    (d / f"{n:02d}{ext}").write_bytes(data)
    return load(pid)


def remove_ref(pid: str, cid: str, name: str) -> dict:
    f = PROJECTS / pid / "cast" / cid / name
    if "/" in name or ".." in name or not f.is_file():
        raise KeyError(name)
    f.unlink()
    return load(pid)


def variant(p: dict, vid: str | None) -> dict:
    """A variant of the project, the first when vid is None."""
    found = next((v for v in p["variants"] if v["id"] == vid), None) if vid else p["variants"][0]
    if not found:
        raise KeyError(vid)
    return found


def characters(pid: str, ids: list[str]) -> list[dict]:
    """The named characters of a project, each with its looks and reference image files, in the order given;
    unknown ids and projects are skipped, so a video outlives a character removed later."""
    try:
        cast = {c["id"]: c for c in _read(pid)["cast"]}
    except KeyError:
        return []
    return [{**cast[i], "files": refs(pid, i)[:REFS_PER_CHARACTER]} for i in ids if i in cast]
