"""Engine JSON -> compact text for an agent. Pure functions: what is left out matters as much as what is shown."""

from __future__ import annotations

from factory.core import formats

NEXT = {
    "script": "show the owner the script, edit_script with their changes, then run(action='approve') to make the video",
    "approved": "queued for generation",
    "generating": "the video is being made: job(id) waits for it",
    "review": "watch the video (path above), fix with edit_script + run('rebuild') or run('redo_frame'); "
    "accept once the owner is happy with it",
    "done": "accepted",
    "failed": "see the error; run('rebuild') retries",
}


def seconds(ep: dict) -> int:
    return round(sum(b["seconds"] for b in (ep.get("beats") or {}).get("beats", [])))


def episode_line(ep: dict) -> str:
    b = ep.get("beats") or {}
    parts = [ep["slug"], ep["status"], ep.get("language") or b.get("language") or "en"]
    if b:
        parts.append(f"{len(b['beats'])} beats ~{seconds(ep)}s")
    return " · ".join(parts + [ep.get("title") or ""])


def qa_lines(qa: dict | None) -> list[str]:
    if not qa:
        return []
    problems = [c for c in qa["checks"] if c["level"] != "info"]
    if not problems:
        return ["qa: ok"]
    return ["qa:"] + [
        f"  {c['level']}{' beat ' + str(c['beat']) if c.get('beat') else ''}: {c['message']}" for c in problems
    ]


def _script(b: dict, full: bool) -> list[str]:
    """The script by its format's fields: short text fields on one line per beat; the English image prompts only with
    full; long markup (svg) never, it only costs context."""
    fmt = formats.load(b.get("format"))
    mode = formats.mode(fmt, b)
    shown = lambda f: f.get("kind") != "svg" and (full or not f.get("english"))  # noqa: E731
    out = [
        f"{f['key']}: {b.get(f['key'], '')}"
        for f in formats.fields(fmt, mode, "script")
        if shown(f) and (f.get("required") or b.get(f["key"]))
    ]
    beat_fields = formats.fields(fmt, mode, "beat")
    inline = [f["key"] for f in beat_fields if f.get("kind", "text") == "text"]
    rest = [f["key"] for f in beat_fields if f["key"] not in inline and shown(f)]
    out.append("beats:")
    for i, x in enumerate(b["beats"], 1):
        out.append(f" {i}. " + " | ".join([str(x.get(k, "")) for k in inline] + [f"{x['seconds']}s"]))
        out += [f"    {k}: {x[k]}" for k in ("vo", *rest) if x.get(k)]
    return out


def episode(ep: dict, qa: dict | None = None, translations: list[dict] | None = None, full: bool = False) -> str:
    b = ep.get("beats") or {}
    out = [f"{ep.get('title') or ep['slug']}  [{ep['slug']}]"]
    facts = [ep["status"], ep.get("language") or b.get("language") or "en"]
    if b:
        facts += [
            f"style {b.get('style')}",
            f"music {b.get('music') or 'by mood'}",
            "voice" if b.get("voice") else "no voice",
        ]
    if ep.get("series") and ep.get("series") != ep["slug"] and not ep.get("translation_of"):
        facts.append(f"series {ep['series']} #{ep.get('episode_index', 1)}")
    if ep.get("translation_of"):
        facts.append(f"translation of {ep['translation_of']}")
    out.append(" · ".join(facts))
    if ep.get("error"):
        out.append(f"error: {ep['error']}")
    if b:
        out += _script(b, full)
    if ep.get("video"):
        out.append(f"video: {ep['video']}")
    out += qa_lines(qa)
    if translations:
        out.append(
            "languages: " + ", ".join(f"{t.get('language')} → {t['slug']} ({t['status']})" for t in translations)
        )
    if ep["status"] in NEXT:
        out.append(f"next: {NEXT[ep['status']]}")
    return "\n".join(out)


def job_line(job: dict) -> str:
    line = f"job {job['id']} {job['kind']}{' ' + job['slug'] if job.get('slug') else ''} · {job['status']}"
    if job["status"] == "running":
        line += f" {round((job.get('progress') or 0) * 100)}%"
        if job.get("stage"):
            line += f" ({job['stage']})"
    if job.get("error"):
        line += f" · {short(job['error'])}"
    return line


def short(error: str, limit: int = 240) -> str:
    """One line of an error: tracebacks and provider chatter stay in the engine log."""
    flat = " ".join(error.split())
    return flat if len(flat) <= limit else flat[:limit] + "…"


def last_log(job: dict, n: int = 3) -> list[str]:
    return [f"  {line}" for line in (job.get("log") or "").strip().splitlines()[-n:] if line.strip()]
