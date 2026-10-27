"""Engine health, machine profile, settings, and the job queue with its live event stream."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from factory import jobs
from factory.core import LANGUAGES, PROFILE, ROOT, defaults, formats, load_profile, save_profile, tilde
from factory.music import library

router = APIRouter()


@router.get("/health")
def health() -> dict:
    from importlib.metadata import version

    return {"ok": True, "root": tilde(ROOT), "version": version("content-factory")}


@router.get("/profile")
def profile() -> dict:
    return load_profile() if PROFILE.exists() else {}


@router.post("/doctor")
def doctor() -> dict:
    from factory import doctor as d

    d.run()
    return load_profile()


class DefaultsIn(BaseModel):
    language: str | None = None
    format: str | None = None
    style: str | None = None
    duration: int | None = None
    voice: bool | None = None


class SettingsIn(BaseModel):
    defaults: DefaultsIn | None = None
    onboarded: bool | None = None


def _mcp_command() -> str:
    return f"claude mcp add -s user content-factory -- {tilde(Path(sys.executable))} -m factory mcp"


@router.get("/settings")
def settings() -> dict:
    return {
        "defaults": defaults(),
        "languages": LANGUAGES,
        "mcp": _mcp_command(),
        "music": len(library.tracks()),
        "onboarded": bool(PROFILE.exists() and load_profile().get("onboarded")),
    }


@router.put("/settings")
def save_settings(body: SettingsIn) -> dict:
    if not PROFILE.exists() and (body.defaults or body.onboarded is not None):
        from factory import doctor

        doctor.run()
    if PROFILE.exists() and (body.defaults or body.onboarded is not None):
        p = load_profile()
        if body.defaults:
            changes = body.defaults.model_dump(exclude_none=True)
            if changes.get("language", "en") not in LANGUAGES:
                raise HTTPException(400, f"language must be one of {', '.join(LANGUAGES)}")
            if changes.get("format") and changes["format"] not in formats.ids():
                raise HTTPException(400, f"format must be one of {', '.join(formats.ids())}")
            p["defaults"] = {**defaults(), **changes}
        if body.onboarded is not None:
            p["onboarded"] = body.onboarded
        save_profile(p)
    return settings()


@router.get("/jobs")
def job_list() -> list[dict]:
    return jobs.list_jobs()


@router.delete("/jobs")
def jobs_clear() -> dict:
    """Clears finished jobs (done, failed, cancelled) from the list; running and queued ones stay."""
    return {"removed": jobs.clear_finished()}


@router.get("/jobs/{job_id}")
def job(job_id: int, wait: float = 0) -> dict:
    """One job; with wait, held until it finishes (at most 55 s), so clients wait without polling."""
    found = jobs.wait_finished(job_id, max(0.0, min(wait, 55.0)))
    if not found:
        raise HTTPException(404, "no such job")
    return found


@router.post("/jobs/{job_id}/cancel")
def job_cancel(job_id: int) -> dict:
    jobs.cancel(job_id)
    return {"ok": True}


@router.get("/events")
async def events() -> StreamingResponse:
    """Server-sent events: the job list every time something changes (and a keep-alive every 15 s)."""

    async def stream():
        seen = -1
        while True:
            seen = await asyncio.to_thread(jobs.wait_change, seen)
            yield f"data: {json.dumps({'jobs': jobs.list_jobs(40)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/setup")
def setup_status() -> dict:
    """What the engine needs on this machine and whether it is there; `ready` once every piece is."""
    from factory import setup

    items = setup.components()
    return {"ready": all(c["ok"] or c.get("optional") for c in items), "components": items}


class SetupIn(BaseModel):
    components: list[str] | None = None  # None: everything installable that is missing


@router.post("/setup")
def setup_install(body: SetupIn) -> dict:
    return {"job": jobs.submit("setup", None, components=body.components)}
