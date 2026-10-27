"""The MCP tools. Nine of them, each answering in a few lines of text; see the package docstring for the rules."""

from __future__ import annotations

import io
import math
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.utilities.types import Image
from mcp_types import ToolAnnotations

from factory.core import formats
from factory.mcp import engine, view
from factory.mcp.engine import EngineError
from factory.studio import compose

INSTRUCTIONS = """Content Factory makes faceless short videos on this machine: AI frames from an image API, depth
parallax, local voice, CC0 music, Remotion render. The factory does not write scripts: you write them from the owner's
brief. Videos usually belong to a project, the owner's channel: catalog('projects') lists them with their variants
(ready settings) and cast (recurring characters); pass project, variant and cast to create and follow the project's
brief. Flow: catalog('format') once for the formats and their rules -> create(topic, script, format) -> show the owner
the script, edit_script on feedback -> run('approve') -> job(id) until done -> episode(slug) gives the video path and
the quality check -> accept once the owner is happy with it. Posting is the owner's job: give them the file path.
Long work runs in the engine's queue; job(id) waits for it (up to 50 s per call), never poll faster.
Texts are in the episode's language; the image prompt fields the format's guide marks as English stay in English."""

server = MCPServer("content-factory", instructions=INSTRUCTIONS)

READ = ToolAnnotations(read_only_hint=True, open_world_hint=False)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False)


def _episode_text(slug: str, full: bool = False) -> str:
    ep = engine.call("GET", f"/api/episodes/{slug}")
    qa = engine.file_json(slug, "out/qa.json") if ep.get("video") else None
    translations = [e for e in engine.call("GET", "/api/episodes") if e.get("translation_of") == slug]
    if ep.get("video"):  # the full path, in the engine's folder, which need not be this process's own
        ep = {**ep, "video": str(engine.episodes() / slug / ep["video"])}
    return view.episode(ep, qa, translations, full)


def _job_text(job: dict) -> str:
    """A job as it stands; once done, what it produced, so the next step needs no extra call."""
    out = [view.job_line(job)]
    if job["status"] in ("queued", "running"):
        return "\n".join(out + view.last_log(job) + [f"call job({job['id']}) again to keep waiting"])
    if job["status"] != "done":
        return out[0]
    if job["kind"] in ("generate", "stages"):
        return "\n\n".join(out + [_episode_text(job["slug"])])
    return "\n".join(out)


def _wait(job_id: int, seconds: int) -> str:
    return _job_text(engine.call("GET", f"/api/jobs/{job_id}", timeout=seconds + 10, wait=seconds))


@server.tool(annotations=READ, structured_output=False)
def status() -> str:
    """Engine state: running and queued jobs, episodes by status, what waits for the owner."""
    eps = engine.call("GET", "/api/episodes")
    active = [j for j in engine.call("GET", "/api/jobs") if j["status"] in ("queued", "running")]
    counts: dict[str, int] = {}
    for e in eps:
        counts[e["status"]] = counts.get(e["status"], 0) + 1
    out = ["episodes: " + (", ".join(f"{k} {v}" for k, v in counts.items()) or "none")]
    out += [view.job_line(j) for j in active] or ["no jobs running"]
    waiting = [e for e in eps if e["status"] in ("script", "review")]
    if waiting:
        out.append("waiting for review:")
        out += [f"  {view.episode_line(e)}" for e in waiting[:10]]
    return "\n".join(out)


@server.tool(annotations=READ, structured_output=False)
def episodes(status: str | None = None, limit: int = 20, project: str | None = None) -> str:
    """Episodes, newest first, one line each: slug · status · language · length · title.
    status filters: draft, script, generating, review, done, failed. project: a project id, its episodes only."""
    eps = [e for e in engine.call("GET", "/api/episodes", project=project) if not status or e["status"] == status]
    lines = [view.episode_line(e) for e in eps[:limit]]
    if len(eps) > limit:
        lines.append(f"… {len(eps) - limit} more")
    return "\n".join(lines) or "no episodes"


@server.tool(annotations=READ, structured_output=False)
def episode(slug: str, full: bool = False, frames: bool = False) -> list[Any]:
    """One episode: script (its texts, beats with their seconds and spoken line), video path, quality check,
    languages, next step. full adds the English image prompts. frames adds one contact sheet of the beat
    frames (about 1000 px): ask for it only when the look matters, an image costs far more than text."""
    out: list[Any] = [_episode_text(slug, full)]
    if frames:
        sheet = _frame_sheet(slug)
        out.append(sheet if sheet else "no frames yet")
    return out


def _frame_sheet(slug: str) -> Image | None:
    from PIL import Image as PILImage
    from PIL import ImageDraw

    files = sorted((engine.episodes() / slug / "work" / "public" / "frames").glob("[0-9][0-9]-916.png"))
    if not files:
        return None
    cols = min(len(files), 6)
    rows = math.ceil(len(files) / cols)
    tile_w = min(1000 // cols, int(1000 / rows * 9 / 16))
    tile_h = tile_w * 16 // 9
    sheet = PILImage.new("RGB", (cols * tile_w, rows * tile_h), "black")
    draw = ImageDraw.Draw(sheet)
    for k, f in enumerate(files):
        with PILImage.open(f) as im:
            x, y = (k % cols) * tile_w, (k // cols) * tile_h
            sheet.paste(im.convert("RGB").resize((tile_w, tile_h)), (x, y))
            draw.rectangle((x, y, x + 26, y + 20), fill="black")
            draw.text((x + 6, y + 4), str(k + 1), fill="white")
    buf = io.BytesIO()
    sheet.save(buf, "JPEG", quality=80)
    return Image(data=buf.getvalue(), format="jpeg")


@server.tool(annotations=WRITE, structured_output=False)
def create(
    topic: str,
    script: dict[str, Any] | None = None,
    language: str | None = None,
    duration: int | None = None,
    style: str | None = None,
    voice: bool | None = None,
    series: str | None = None,
    style_prompt: str | None = None,
    format: str | None = None,
    project: str | None = None,
    variant: str | None = None,
    cast: list[str] | None = None,
) -> str:
    """Start a video. script: the full beats.json you wrote by catalog('format', format=...); without it the episode
    opens with an empty script for the owner to fill in the app. format: a format id from catalog('format'), the
    owner's default when omitted. Unset options take the owner's defaults from Settings.
    style: an id from catalog('styles', format=...), or 'custom' with style_prompt. series: slug of an episode to
    continue. Several episodes on one topic: call create once per episode with the same series.
    project, variant: from catalog('projects'); the variant's settings replace the owner's defaults. cast: ids of
    the project's characters in the video, the variant's when omitted; their looks go into every frame on their own,
    so the script only names them."""
    try:
        r = engine.call(
            "POST",
            "/api/compose",
            {
                "topic": topic,
                "script": script,
                "language": language,
                "duration": duration,
                "style": style,
                "style_prompt": style_prompt,
                "voice": voice,
                "series": series,
                "format": format,
                "project": project,
                "variant": variant,
                "cast": cast,
            },
        )
    except EngineError as e:
        return f"not created: {e}"
    warnings = "".join(f"\n- {w}" for w in r.get("warnings") or [])
    return _episode_text(r["slug"]) + (f"\nwarnings:{warnings}" if warnings else "")


def merge_script(beats: dict, changes: dict) -> dict:
    """beats.json with changes applied; "beats" may be {number: patch} or a full list."""
    out = {**beats, **changes}
    patches = changes.get("beats")
    if isinstance(patches, dict):
        merged = [dict(x) for x in beats["beats"]]
        for n, patch in patches.items():
            if not str(n).isdigit() or not 1 <= int(n) <= len(merged):
                raise ValueError(f"no beat {n}; the script has {len(merged)}")
            merged[int(n) - 1].update(patch)
        out["beats"] = merged
    return out


@server.tool(annotations=WRITE, structured_output=False)
def edit_script(slug: str, changes: dict[str, Any]) -> str:
    """Change a script before (re)making the video. changes merges into beats.json: top-level fields of the format
    (see its guide), music (track id from catalog('music') or 'none'), style, voice; and "beats": {"2": {"vo": "...",
    "seconds": 6}} to change beats by number, or a full list to replace them all. Spoken lines: numbers in words,
    [pause 0.6] for silence."""
    ep = engine.call("GET", f"/api/episodes/{slug}")
    if not ep.get("beats"):
        return "this episode has no script yet"
    try:
        b = merge_script(ep["beats"], changes)
    except ValueError as e:
        return str(e)
    try:
        r = engine.call("PUT", f"/api/episodes/{slug}/beats", b)
    except EngineError as e:
        return f"not saved: {e}"
    warnings = r.get("warnings") or []
    return (
        "saved"
        + ("".join(f"\n- {w}" for w in warnings) if warnings else "")
        + ("\nrun('rebuild') to remake the video" if ep["status"] in ("review", "done") else "")
    )


@server.tool(annotations=WRITE, structured_output=False)
def run(
    slug: str,
    action: Literal["approve", "rebuild", "redo_frame", "translate"],
    beat: int | None = None,
    language: str | None = None,
    texts: dict[str, Any] | None = None,
    stages: list[str] | None = None,
    wait: int = 0,
) -> str:
    """Start work on an episode in the engine queue and return its job.
    approve: make the video from the script (minutes; refused while fields are empty).
    rebuild: remake after edits; only what changed is recomputed (stages narrows it: frames, depth, transitions, tts,
    align, render, qa).
    redo_frame: a new take of one beat's frame (beat 1 redoes all, the others are edits of it).
    translate: a copy in another language (catalog('voices') lists them) that reuses the frames and opens as a
    script; texts is your translation of the fields the format's guide names as texts {<field>: ..., beats:
    [{<field>: ...}] in beat order}, without it the copy keeps the original texts."""
    if action == "approve":
        r = engine.call("POST", f"/api/episodes/{slug}/approve")
    elif action == "rebuild":
        r = engine.call("POST", f"/api/episodes/{slug}/rerun", stages)
    elif action == "redo_frame":
        if not beat:
            return "redo_frame needs beat"
        r = engine.call("POST", f"/api/episodes/{slug}/beats/{beat}/regenerate")
    else:
        if not language:
            return "translate needs language"
        try:
            r = engine.call("POST", f"/api/episodes/{slug}/translate", {"language": language, "texts": texts})
        except EngineError as e:
            return f"not translated: {e}"
        return _episode_text(r["slug"])
    return _wait(r["job"], max(0, min(wait, 50)))


@server.tool(annotations=WRITE, structured_output=False)
def job(job_id: int, wait: int = 50, cancel: bool = False) -> str:
    """Wait for a job (up to `wait` seconds, max 50) and say how it ended: a finished script or video comes back
    with the episode, so no extra call is needed. cancel stops it instead."""
    if cancel:
        engine.call("POST", f"/api/jobs/{job_id}/cancel")
        return f"job {job_id} cancelled"
    return _wait(job_id, max(0, min(wait, 50)))


@server.tool(annotations=WRITE, structured_output=False)
def accept(slug: str, caption: str = "") -> str:
    """Mark the video done and keep a post caption with it; answers with the file to post."""
    return "accepted: " + engine.call("POST", f"/api/episodes/{slug}/accept", {"caption": caption})["video"]


@server.tool(annotations=READ, structured_output=False)
def catalog(
    kind: Literal["format", "styles", "music", "voices", "projects"], language: str = "en", format: str | None = None
) -> str:
    """format: with a format id, how to write a script in it (rules, fields, a finished example); without one, the
    formats (id — title: description), or the guide itself when there is only one. Read it before your first create.
    styles of a format (id — title, tags; the default format without one), music (id — moods), voices (language —
    engine, voice), projects (the owner's channels: brief, variants with their settings, cast with looks)."""
    if kind == "projects":
        return "\n\n".join(map(view.project, engine.call("GET", "/api/projects"))) or "no projects"
    if kind == "format":
        ids = formats.ids()
        if format or len(ids) == 1:
            try:
                return compose.guide(language, format)
            except ValueError as e:
                return str(e)
        return "\n".join(f"{f['id']} — {f['title']}: {f['description']}" for f in map(formats.load, ids))
    if kind == "styles":
        try:
            found = engine.call("GET", "/api/styles", format=format)
        except EngineError as e:
            return str(e)
        return "\n".join(f"{s['id']} — {s['title']}: {', '.join(s['tags'])}" for s in found)
    if kind == "music":
        tracks = engine.call("GET", "/api/music")
        if not tracks:
            return "library empty: factory music fetch --starter"
        licences = {t["license"] for t in tracks}
        return (
            "\n".join(f"{t['id']} — {', '.join(t.get('moods', []))}" for t in tracks) + f"\nall {', '.join(licences)}"
        )
    return "\n".join(f"{lang} — {v['engine']}, {v['speaker']}" for lang, v in engine.call("GET", "/api/voices").items())


def main() -> None:
    server.run("stdio")
