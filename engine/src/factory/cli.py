"""The `factory` command. Episode work goes through the engine's HTTP API with the same commands the MCP server
offers (factory.mcp.server), so the app, an agent and the terminal share one queue and one set of rules. Only setting
up the machine, the music library and the servers themselves run locally."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _json(arg: str | None):
    """A JSON argument: inline, a file path, or - for stdin."""
    if arg is None:
        return None
    text = sys.stdin.read() if arg == "-" else Path(arg).read_text(encoding="utf-8") if Path(arg).is_file() else arg
    return json.loads(text)


def _follow(reply: str) -> str:
    """A terminal waits for the job to end: keep calling job() while the reply says to."""
    from factory.mcp import server

    while m := re.search(r"call job\((\d+)\) again", reply):
        print(reply.splitlines()[0], file=sys.stderr, flush=True)
        reply = server.job(int(m.group(1)))
    return reply


def main() -> None:
    ap = argparse.ArgumentParser(prog="factory", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True, metavar="command")

    sub.add_parser("status", help="running jobs, episodes by status, what waits for review")
    p = sub.add_parser("episodes", help="episodes, newest first")
    p.add_argument("--status", help="draft, script, generating, review, done or failed")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--project", help="a project id, its episodes only")
    p = sub.add_parser("episode", help="one episode: script, video, quality check, next step")
    p.add_argument("slug")
    p.add_argument("--full", action="store_true", help="include the image prompts")
    p = sub.add_parser("create", help="start a video, empty or from a finished script")
    p.add_argument("topic")
    p.add_argument("--script", help="beats.json: a file, inline JSON or - for stdin")
    p.add_argument("--format", help="a format id from `factory catalog format`")
    p.add_argument("--language")
    p.add_argument("--duration", type=int)
    p.add_argument("--style")
    p.add_argument("--style-prompt")
    p.add_argument("--voice", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--series", help="slug of an episode to continue")
    p.add_argument("--project", help="a project id from `factory catalog projects`")
    p.add_argument("--variant", help="one of the project's variants, its first by default")
    p.add_argument("--cast", help="comma-separated character ids, the variant's by default")
    p = sub.add_parser("edit", help="merge changes into a script")
    p.add_argument("slug")
    p.add_argument("changes", help='JSON, e.g. {"hook": "...", "beats": {"2": {"vo": "..."}}}; a file or - for stdin')
    p = sub.add_parser("run", help="approve, rebuild, redo_frame or translate, and wait for the job")
    p.add_argument("slug")
    p.add_argument("action", choices=["approve", "rebuild", "redo_frame", "translate"])
    p.add_argument("--beat", type=int, help="redo_frame: the beat")
    p.add_argument("--language", help="translate: the target language")
    p.add_argument("--texts", help="translate: the translated texts as JSON, a file or -")
    p.add_argument("--stages", help="rebuild: comma-separated stages, default all")
    p.add_argument("--no-wait", action="store_true", help="return once the job is queued")
    p = sub.add_parser("job", help="wait for a job and say how it ended")
    p.add_argument("id", type=int)
    p.add_argument("--cancel", action="store_true")
    p = sub.add_parser("accept", help="mark the video done and keep its post caption")
    p.add_argument("slug")
    p.add_argument("--caption", default="")
    p = sub.add_parser("catalog", help="formats and how to write them, styles, music, voices, projects")
    p.add_argument("kind", choices=["format", "styles", "music", "voices", "projects"])
    p.add_argument("--format")
    p.add_argument("--language", default="en")

    p = sub.add_parser("format", help="read a format's files into a folder, or save a folder as an own format")
    p.add_argument("action", choices=["show", "save", "remove"])
    p.add_argument("id")
    p.add_argument("folder", nargs="?", help="show: write the files here instead of printing; save: read them here")

    sub.add_parser("doctor", help="detect OS, GPU and tools, write profile.yaml")
    p = sub.add_parser("setup", help="show what is installed; with names (or 'all') install them")
    p.add_argument("components", nargs="*", help="component ids, or all")
    p = sub.add_parser("music", help="background music library")
    p.add_argument("action", choices=["fetch", "list"])
    p.add_argument("slugs", nargs="*", help="OpenGameArt page slugs (CC0 only)")
    p.add_argument("--moods", default="", help="comma-separated moods for the fetched tracks")
    p.add_argument("--starter", action="store_true", help="import the starter set from music/starter.yaml")
    p = sub.add_parser("serve", help="the engine: local HTTP API for the app, the MCP server and this command")
    p.add_argument("--port", type=int, default=8790)
    sub.add_parser("mcp", help="MCP server over stdio, for Claude and other agents")
    # the queue runs every stage as its own process so a job can be cancelled; not meant to be typed
    p = sub.add_parser("stage")
    p.add_argument("episode")
    p.add_argument("name")
    args = ap.parse_args()

    if args.cmd in ("status", "episodes", "episode", "create", "edit", "run", "job", "accept", "catalog", "format"):
        print(_command(args))
    elif args.cmd == "music":
        _music(args)
    elif args.cmd == "mcp":
        from factory.mcp.server import main as mcp_main

        mcp_main()
    elif args.cmd == "serve":
        from factory import api

        api.run(args.port)
    elif args.cmd == "doctor":
        from factory import doctor

        doctor.run()
    elif args.cmd == "setup":
        from factory import doctor, setup

        todo = setup.missing() if args.components == ["all"] else args.components
        for name in todo:
            setup.install(name)
        if todo:
            doctor.run()
        for c in setup.components():
            print(
                f"{'ok ' if c['ok'] else '-- '} {c['id']}: {c['detail']}"
                + ("" if c["ok"] or c.get("install") else f"  ({c['command']})")
            )
    else:
        from factory import stages
        from factory.core import Episode, load_profile

        stages.run(Episode.load(args.episode), load_profile(), [args.name])


def _command(args) -> str:
    from factory.mcp import server

    if args.cmd == "status":
        return server.status()
    if args.cmd == "episodes":
        return server.episodes(args.status, args.limit, args.project)
    if args.cmd == "episode":
        return server.episode(args.slug, args.full)[0]
    if args.cmd == "create":
        return server.create(
            args.topic,
            _json(args.script),
            args.language,
            args.duration,
            args.style,
            args.voice,
            args.series,
            args.style_prompt,
            args.format,
            args.project,
            args.variant,
            args.cast.split(",") if args.cast else None,
        )
    if args.cmd == "format":
        return _format(args)
    if args.cmd == "edit":
        return server.edit_script(args.slug, _json(args.changes) or {})
    if args.cmd == "run":
        stages = args.stages.split(",") if args.stages else None
        reply = server.run(args.slug, args.action, args.beat, args.language, _json(args.texts), stages)
        return reply if args.no_wait else _follow(reply)
    if args.cmd == "job":
        return server.job(args.id, cancel=args.cancel) if args.cancel else _follow(server.job(args.id))
    if args.cmd == "accept":
        return server.accept(args.slug, args.caption)
    return server.catalog(args.kind, args.language, args.format)


def _format(args) -> str:
    """Formats travel as folders on disk; the engine gets and gives them as files by path."""
    from factory.mcp import server
    from factory.studio.formats import TEXT

    if args.action == "remove":
        return server.save_format(args.id, remove=True)
    if args.action == "save":
        root = Path(args.folder or ".")
        files = {
            p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
            for p in sorted(root.rglob("*"))
            if p.is_file() and p.suffix in TEXT
        }
        return server.save_format(args.id, files)
    if not args.folder:
        return server.format_source(args.id)
    from factory.mcp import engine

    src = engine.call("GET", f"/api/formats/{args.id}/source")
    for rel, text in src["files"].items():
        (Path(args.folder) / rel).parent.mkdir(parents=True, exist_ok=True)
        (Path(args.folder) / rel).write_text(text, encoding="utf-8")
    return f"{len(src['files'])} files of {args.id} in {args.folder}"


def _music(args) -> None:
    import yaml

    from factory.music import fetch, library

    if args.action == "list":
        for t in library.tracks():
            print(f"{t['id']}: {t['title']} by {t['author']} ({t['license']}) - {', '.join(t['moods'])}")
        return
    todo = [{"slug": s, "moods": [m for m in args.moods.split(",") if m]} for s in args.slugs]
    if args.starter:
        todo += yaml.safe_load(library.STARTER.read_text(encoding="utf-8"))
    for item in todo:
        try:
            t = fetch.fetch(item["slug"], item.get("moods", []), item.get("default", False))
            print(f"music: {t['id']} ({t['title']} by {t['author']})", flush=True)
        except Exception as e:  # one bad page must not stop the rest
            print(f"music: skip {item['slug']}: {e}", flush=True)
