"""Formats (the shipped ones and the owner's own, which agents add), their styles, and music."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from factory import jobs
from factory.core import formats
from factory.music import library
from factory.studio import formats as own
from factory.studio import storage as disk
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


@router.get("/formats/{fid}/guide")
def format_guide(fid: str, language: str = "en") -> dict:
    """How to write a script in the format, for an agent: its guide with a finished example."""
    from factory.studio import compose

    return {"guide": compose.guide(language, _format(fid))}


@router.get("/formats/{fid}/source")
def format_source(fid: str) -> dict:
    """Every text file of a format: what an agent copies to make its own."""
    return own.source(_format(fid))


class FormatIn(BaseModel):
    files: dict[str, str]  # path inside the format folder -> text


@router.put("/formats/{fid}")
def save_format(fid: str, body: FormatIn) -> dict:
    """Add or replace an own format; it is checked before it goes live, and nothing changes when it fails."""
    try:
        return own.save(fid, body.files)
    except ValueError as e:
        raise HTTPException(400, str(e)) from None


@router.delete("/formats/{fid}")
def remove_format(fid: str) -> dict:
    try:
        own.remove(fid, disk.trash())
    except KeyError:
        raise HTTPException(404, "no such own format; shipped formats stay") from None
    return {"ok": True}


@router.get("/styles")
def styles(format: str | None = None) -> list[dict]:
    return store.styles(_format(format))


@router.post("/styles/{sid}/preview")
def style_preview(sid: str, format: str | None = None) -> dict:
    return {"job": jobs.submit("style_preview", None, style=sid, format=_format(format))}
