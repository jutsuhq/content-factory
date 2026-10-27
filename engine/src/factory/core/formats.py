"""Formats: one folder per format, recognised by its format.yaml: the ones shipped in FORMATS and the owner's own in
OWN_FORMATS (added by an agent through the engine, see studio.formats). The engine knows no format by name: it lists
the folders and reads the one a script names (beats.json `format`), else the default one."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from factory.core.paths import FORMATS, OWN_FORMATS


def folders() -> dict[str, Path]:
    """Every format's folder by id; a shipped format wins over an own one of the same name."""
    found: dict[str, Path] = {}
    for root in (OWN_FORMATS, FORMATS):
        if root.is_dir():
            # a dot folder is a version being saved or replaced (studio.formats.save), not a format
            found |= {d.name: d for d in root.iterdir() if (d / "format.yaml").is_file() and d.name[0] != "."}
    return found


def ids() -> list[str]:
    return sorted(folders())


def default_id() -> str:
    """The owner's default from Settings when that format exists, else the first one found."""
    from factory.core.profile import defaults

    fid = defaults()["format"]
    if not fid:
        raise SystemExit(f"no formats in {FORMATS}")
    return fid


def load(fid: str | None = None) -> dict:
    """format.yaml of one format (the default one for None), with its id and folder."""
    fid = fid or default_id()
    d = folders().get(fid)
    if not d:
        raise ValueError(f"unknown format {fid}; formats: {', '.join(ids())}")
    own = d.parent == OWN_FORMATS
    return {**yaml.safe_load((d / "format.yaml").read_text(encoding="utf-8")), "id": fid, "dir": d, "own": own}


def examples(fmt: dict) -> list:
    """The format's finished scripts, examples/*.beats.json."""
    return sorted((fmt["dir"] / "examples").glob("*.beats.json"))


def schema(fmt: dict) -> dict:
    return json.loads((fmt["dir"] / "beats.schema.json").read_text(encoding="utf-8"))


def styles(fid: str | None = None) -> dict:
    p = load(fid)["dir"] / "styles.yaml"
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}


def mode(fmt: dict, beats: dict) -> str:
    """The script's render mode; a script without one uses the format's first."""
    return beats.get("render_mode") or next(iter(fmt["render_modes"]))


def fields(fmt: dict, mode_id: str, level: str) -> list[dict]:
    """Field declarations of one level ("script" or "beat"): the format's own, then the render mode's."""
    return (fmt.get("fields") or {}).get(level, []) + (fmt["render_modes"][mode_id].get("fields") or {}).get(level, [])


def keys(fmt: dict, mode_id: str, level: str, flag: str) -> list[str]:
    """Keys of the fields that carry a flag such as required, english or translate."""
    return [f["key"] for f in fields(fmt, mode_id, level) if f.get(flag)]


def style_ids(fmt: dict, mode_id: str) -> list[str]:
    """What `style` may be in a render mode: the format's presets, or the mode's fixed looks."""
    style = fmt["render_modes"][mode_id].get("style", "presets")
    return list(styles(fmt["id"])) if style == "presets" else [x["id"] for x in style["looks"]]


def summary(fmt: dict) -> dict:
    """What the app and agents see of a format: everything format.yaml declares but the folder."""
    return {k: v for k, v in fmt.items() if k != "dir"}
