"""The owner's own formats: an agent reads any format whole (source), writes a new one or a changed copy (save) and
the engine checks it before it goes live, so a broken format never reaches the app. Shipped formats are read-only;
own ones live in OWN_FORMATS and can be replaced or removed."""

from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from factory.core import FORMATS, OWN_FORMATS, formats
from factory.stages import ORDER

ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")
TEXT = {".yaml", ".yml", ".json", ".md", ".txt", ".ts", ".tsx", ".css", ".svg"}
MAX_BYTES = 2_000_000  # the whole format; templates and guides are small, images are not sent this way


def source(fid: str) -> dict:
    """Every text file of a format, by path inside its folder, and the names of the others (preview images)."""
    d = formats.load(fid)["dir"]
    files, other = {}, []
    for f in sorted(p for p in d.rglob("*") if p.is_file()):
        rel = f.relative_to(d).as_posix()
        if f.suffix in TEXT:
            files[rel] = f.read_text(encoding="utf-8")
        else:
            other.append(rel)
    return {"id": fid, "own": d.parent == OWN_FORMATS, "files": files, "other": other}


def _declared(d: Path) -> list[str]:
    """What is wrong with format.yaml in d, and with the files its render modes need."""
    if not (d / "format.yaml").is_file():
        return ["format.yaml is missing"]
    try:
        fmt = yaml.safe_load((d / "format.yaml").read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        return [f"format.yaml: {e}"]
    keys = ("title", "description", "template", "duration_seconds")
    out = [f"format.yaml: {k} is missing" for k in keys if k not in fmt]
    modes = fmt.get("render_modes") or {}
    if not modes:
        out.append("format.yaml: render_modes needs at least one mode")
    for mid, m in modes.items():
        if unknown := [s for s in m.get("stages", []) if s not in ORDER]:
            out.append(f"render mode {mid}: unknown stages {unknown}; stages: {', '.join(ORDER)}")
        if m.get("style", "presets") == "presets" and not (d / "styles.yaml").is_file():
            out.append(f"render mode {mid} uses style presets: styles.yaml is missing")
        for name in ("first_frame.txt", "next_frame.txt") if "frames" in m.get("stages", []) else ():
            if not ((d / "prompts" / mid / name).is_file() or (d / "prompts" / name).is_file()):
                out.append(f"render mode {mid} makes frames: prompts/{name} is missing")
    return out


def _files(d: Path) -> list[str]:
    """What is wrong with the schema, guide, template and examples in d."""
    out = []
    try:
        Draft202012Validator.check_schema(json.loads((d / "beats.schema.json").read_text(encoding="utf-8")))
    except FileNotFoundError:
        out.append("beats.schema.json is missing")
    except Exception as e:  # bad JSON or a schema that is not one
        out.append(f"beats.schema.json: {str(e).splitlines()[0]}")
    if not (d / "guide.md").is_file():
        out.append("guide.md is missing: it is what an agent writes scripts by")
    index = next((p for p in (d / "template" / "index.ts", d / "template" / "index.tsx") if p.is_file()), None)
    if not index or "template" not in index.read_text(encoding="utf-8"):
        out.append("template/index.ts must export `template` ({ id, component, empty })")
    if not list((d / "examples").glob("*.beats.json")):
        out.append("examples/ needs a finished script, <name>.beats.json")
    return out


def _scripts(fid: str) -> list[str]:
    """The format's example scripts, checked like any script saved in it."""
    from factory.studio import compose

    out = []
    for ex in formats.examples(formats.load(fid)):
        b = {"format": fid, **json.loads(ex.read_text(encoding="utf-8"))}
        try:
            out += [f"{ex.name}: {p}" for p in compose.problems(b) if p.startswith("schema")]
            out += [f"{ex.name}: empty {m}" for m in compose.missing(b)]
        except (ValueError, KeyError) as e:
            out.append(f"{ex.name}: {e}")
    return out


def _write(d: Path, files: dict[str, str]) -> None:
    shutil.rmtree(d, ignore_errors=True)
    for rel, text in files.items():
        p = Path(rel)
        if p.is_absolute() or ".." in p.parts or p.suffix not in TEXT:
            shutil.rmtree(d, ignore_errors=True)
            raise ValueError(f"{rel}: a path inside the format folder, a text file ({', '.join(sorted(TEXT))})")
        (d / p).parent.mkdir(parents=True, exist_ok=True)
        (d / p).write_text(text, encoding="utf-8")


def save(fid: str, files: dict[str, str]) -> dict:
    """Write an own format from its files (paths inside its folder) and check it; a format that fails the checks is
    not kept, and the one it was replacing stays. ValueError carries everything that is wrong."""
    if not ID.match(fid):
        raise ValueError("a format id is 2-41 characters: lowercase letters, digits and dashes")
    if (FORMATS / fid / "format.yaml").is_file():
        raise ValueError(f"{fid} ships with the factory and cannot be replaced; save a copy under a new id")
    if sum(len(t.encode()) for t in files.values()) > MAX_BYTES:
        raise ValueError(f"the format is over {MAX_BYTES // 1_000_000} MB of text")
    new, old, live = OWN_FORMATS / f".new-{fid}", OWN_FORMATS / f".old-{fid}", OWN_FORMATS / fid
    _write(new, files)
    if (live / "previews").is_dir() and not (new / "previews").exists():
        shutil.copytree(live / "previews", new / "previews")  # style previews made for the earlier version
    if problems := _declared(new) + _files(new):
        shutil.rmtree(new, ignore_errors=True)
        raise ValueError("; ".join(problems))
    # the scripts are checked through the engine's own loading, so the new version goes live first and is rolled
    # back when they fail
    shutil.rmtree(old, ignore_errors=True)
    if live.exists():
        live.rename(old)
    new.rename(live)
    if problems := _scripts(fid):
        shutil.rmtree(live)
        if old.exists():
            old.rename(live)
        raise ValueError("; ".join(problems))
    shutil.rmtree(old, ignore_errors=True)
    fmt = formats.load(fid)
    return {"id": fid, "title": fmt["title"], "render_modes": list(fmt["render_modes"]), "files": len(files)}


def remove(fid: str, trash: Path) -> None:
    """Move an own format to the trash; its videos keep their scripts but cannot be rebuilt until it is back."""
    if not (OWN_FORMATS / fid / "format.yaml").is_file() or not ID.match(fid):
        raise KeyError(fid)
    trash.mkdir(parents=True, exist_ok=True)
    (OWN_FORMATS / fid).rename(trash / f"format-{fid}-{int(time.time())}")
