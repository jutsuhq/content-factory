"""Projects: the channels videos are made for, each with its variants (ready settings) and its cast of characters."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile

from factory.core import projects
from factory.studio import storage as disk

router = APIRouter()


def _do(fn, *args):
    try:
        return fn(*args)
    except KeyError:
        raise HTTPException(404, "no such project, character or file") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from None


@router.get("/projects")
def all_projects() -> list[dict]:
    return projects.all_projects()


@router.post("/projects")
def create(body: dict) -> dict:
    """A new project from {name, platform, handle, color, brief, variants?, cast?}."""
    return _do(projects.create, body)


@router.get("/projects/{pid}")
def project(pid: str) -> dict:
    return _do(projects.load, pid)


@router.put("/projects/{pid}")
def save(pid: str, body: dict) -> dict:
    """Replace the project: its channel details, variants and cast."""
    return _do(projects.save, pid, body)


@router.delete("/projects/{pid}")
def remove(pid: str) -> dict:
    """Moves the project to the trash; its videos stay in the library."""
    _do(projects.remove, pid, disk.trash())
    return {"ok": True}


@router.post("/projects/{pid}/cast/{cid}/refs")
async def add_ref(pid: str, cid: str, file: UploadFile) -> dict:
    """Add a reference image of a character."""
    return _do(projects.add_ref, pid, cid, file.filename or "", await file.read())


@router.delete("/projects/{pid}/cast/{cid}/refs/{name}")
def remove_ref(pid: str, cid: str, name: str) -> dict:
    return _do(projects.remove_ref, pid, cid, name)
