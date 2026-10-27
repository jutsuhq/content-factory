"""Storage settings: where accepted videos go, disk use, clearing the cache and the trash, opening folders."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from factory.core import EPISODES, PROFILE, desktop, load_profile, save_profile, tilde
from factory.core import storage as current
from factory.studio import storage

router = APIRouter()


def _view() -> dict:
    s = current()
    return {
        **s,
        "export_shown": tilde(Path(s["export_dir"])),
        "episodes_dir": tilde(EPISODES),
        "usage": storage.usage(),
    }


@router.get("/storage")
def get_storage() -> dict:
    return _view()


class StorageIn(BaseModel):
    export_dir: str | None = None
    copy_on_accept: bool | None = None
    clean_after_accept: bool | None = None


@router.put("/storage")
def save_storage(body: StorageIn) -> dict:
    changes = body.model_dump(exclude_none=True)
    if "export_dir" in changes:
        folder = Path(changes["export_dir"]).expanduser()
        if not folder.is_absolute():
            raise HTTPException(400, "the folder must be a full path")
        changes["export_dir"] = str(folder)
    if PROFILE.exists():
        p = load_profile()
        p["storage"] = {**current(), **changes}
        save_profile(p)
    return _view()


@router.post("/storage/choose-folder")
def choose_folder() -> dict:
    """Opens the system folder picker; a picked folder is saved as the export folder."""
    start = Path(current()["export_dir"])
    picked = desktop.choose_folder(start if start.exists() else Path.home())
    return save_storage(StorageIn(export_dir=str(picked))) if picked else _view()


@router.post("/storage/clear-cache")
def clear_cache() -> dict:
    return {"freed": storage.clear_cache(), **_view()}


@router.post("/storage/empty-trash")
def empty_trash() -> dict:
    return {"freed": storage.empty_trash(), **_view()}


@router.post("/storage/open/{which}")
def open_folder(which: Literal["episodes", "export"]) -> dict:
    folder = EPISODES if which == "episodes" else Path(current()["export_dir"])
    folder.mkdir(parents=True, exist_ok=True)
    desktop.open_file(folder)
    return {"ok": True}
