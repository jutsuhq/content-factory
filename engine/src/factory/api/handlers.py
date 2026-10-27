"""What each queued job kind does. A handler gets the job row and a `log(line)`; `<kind>:failed` runs after one
throws."""

from __future__ import annotations

from factory import jobs, stages
from factory.core import Episode, formats, load_profile
from factory.studio import store


def _generate(job: dict, log) -> None:
    slug = job["slug"]
    store.save_meta(slug, status="generating", error=None)
    jobs.run_stages(job["id"], slug, stages.plan(Episode.load(slug), job["params"].get("stages")), log)
    store.save_meta(slug, status="review")


def _generate_failed(job: dict, _log) -> None:
    row = jobs.get(job["id"])
    store.save_meta(job["slug"], status="failed", error=(row or {}).get("error"))


def _style_preview(job: dict, log) -> None:
    from factory.providers.image import ImageJob, run_jobs
    from factory.stages.frames import crop_916

    sid, fid = job["params"]["style"], job["params"].get("format") or formats.default_id()
    s = next(x for x in store.styles(fid) if x["id"] == sid)
    prompt = (
        f"{s['prompt']} Scene: a small town square at golden hour with a fountain, a few people and trees, "
        "wide vertical composition. No text, no letters, no logos, no watermark."
    )
    out = store.preview_path(fid, sid)
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = out.with_name(f"{sid}-raw.png")
    errors = run_jobs([ImageJob(prompt, raw)], load_profile()["providers"]["image"], attempts=2)
    if errors:
        raise RuntimeError(errors[0])
    crop_916(raw, out)
    raw.unlink()
    log(f"preview {sid}")


def _setup(job: dict, log) -> None:
    from factory import doctor, setup

    for name in job["params"].get("components") or setup.missing():
        setup.install(name, log)
    doctor.run()


HANDLERS = {
    "generate": _generate,
    "generate:failed": _generate_failed,
    "stages": _generate,
    "stages:failed": _generate_failed,
    "style_preview": _style_preview,
    "setup": _setup,
}
