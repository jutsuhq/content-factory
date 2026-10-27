"""Formats, their styles, and music."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from factory import jobs
from factory.core import formats
from factory.music import library
from factory.studio import store

router = APIRouter()


@router.get("/music")
def music() -> list[dict]:
    return [{**t, "url": f"/files/music/{t['file']}"} for t in library.tracks()]


def _format(fid: str | None) -> str:
    try:
        return formats.load(fid)["id"]
    except ValueError as e:
        raise HTTPException(404, str(e)) from None


@router.get("/formats")
def format_list() -> list[dict]:
    """Every format, the default one first."""
    first = formats.default_id()
    return [formats.summary(formats.load(f)) for f in sorted(formats.ids(), key=lambda f: f != first)]


@router.get("/styles")
def styles(format: str | None = None) -> list[dict]:
    return store.styles(_format(format))


@router.post("/styles/{sid}/preview")
def style_preview(sid: str, format: str | None = None) -> dict:
    return {"job": jobs.submit("style_preview", None, style=sid, format=_format(format))}
