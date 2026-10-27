"""Image providers: which ones exist, their keys (kept in DATA/.env, never sent back) and how many parallel workers
each gets in the profile."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from factory.core import PROFILE, load_profile, save_profile, secrets
from factory.providers import image
from factory.providers.image.pool import PRIVATE, private

router = APIRouter()


def _listing() -> list[dict]:
    workers = ((load_profile() if PROFILE.exists() else {}).get("providers") or {}).get("image") or {}
    out = [
        {**p, "key_set": bool(secrets.get(p["key"])), "enabled": int(workers.get(p["id"], 0))} for p in image.PROVIDERS
    ]
    for pid in PRIVATE:  # optional local workers, absent from a public checkout
        out.append(
            {
                "id": pid,
                "title": pid,
                "key": None,
                "signup": None,
                "price": None,
                "workers": private.DEFAULTS.get(pid, 1),
                "edits": True,
                "note": "local worker",
                "key_set": True,
                "enabled": int(workers.get(pid, 0)),
                "private": True,
            }
        )
    return out


class ImagesIn(BaseModel):
    keys: dict[str, str] = {}
    workers: dict[str, int] = {}


@router.get("/images")
def images() -> list[dict]:
    return _listing()


@router.put("/images")
def save_images(body: ImagesIn) -> list[dict]:
    known = {p["key"] for p in image.PROVIDERS}
    if bad := set(body.keys) - known:
        raise HTTPException(400, f"unknown keys: {', '.join(sorted(bad))}")
    if body.keys:
        secrets.put(**{k: v.strip() for k, v in body.keys.items()})
    if body.workers:
        profile = load_profile() if PROFILE.exists() else {}
        providers = profile.setdefault("providers", {})
        pool = dict(providers.get("image") or {})
        for pid, n in body.workers.items():
            if n > 0:
                pool[pid] = min(n, 8)
            else:
                pool.pop(pid, None)
        providers["image"] = pool
        save_profile(profile)
    return _listing()


@router.post("/images/{provider_id}/check")
def check_image(provider_id: str) -> dict:
    try:
        return {"message": image.check(provider_id)}
    except RuntimeError as e:
        raise HTTPException(400, str(e)) from None
