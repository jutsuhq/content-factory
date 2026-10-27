"""frames: one locked scene per beat from the format's prompts/first_frame.txt, every later one edited from the first
with prompts/next_frame.txt.

The first frame sets the look and is made alone; the rest are edits of it and run in parallel.
Each frame is cached by its prompt and references, so editing one beat regenerates one frame.
"""

from __future__ import annotations

import yaml
from PIL import Image

from factory.core import Episode, digest, fresh, mark
from factory.providers.image import ImageJob, run_jobs

ASPECT = 9 / 16


def crop_916(src, dst) -> None:
    im = Image.open(src).convert("RGB")
    w, h = im.size
    if w / h > ASPECT:
        nw = round(h * ASPECT)
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = round(w / ASPECT)
        im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    im.save(dst)


def _prompts(ep: Episode) -> list[str]:
    b = ep.beats
    presets = yaml.safe_load((ep.format_dir / "styles.yaml").read_text(encoding="utf-8"))
    style = b.get("style_prompt") or presets[b["style"]]["prompt"]
    first = (ep.format_dir / "prompts" / "first_frame.txt").read_text(encoding="utf-8").strip()
    edit = (ep.format_dir / "prompts" / "next_frame.txt").read_text(encoding="utf-8").strip()
    # the format's prompt templates name script and beat fields as {field}; {style} is the style text
    top = {k: v for k, v in b.items() if k != "beats"}
    return [first.format_map({**top, **b["beats"][0], "style": style})] + [
        edit.format_map({**top, **beat, "style": style}) for beat in b["beats"][1:]
    ]


def run(ep: Episode, profile: dict) -> None:
    d = ep.work("frames")
    prompts = _prompts(ep)
    raw = [d / f"{i:02d}.png" for i in range(1, len(prompts) + 1)]

    keys = [digest(prompts[0])]
    if not fresh(raw[0], keys[0]):
        errors = run_jobs([ImageJob(prompts[0], raw[0])], profile["providers"]["image"])
        if errors:
            raise SystemExit("style frame failed: " + errors[0])
        mark(raw[0], keys[0])

    keys += [digest(p, raw[0]) for p in prompts[1:]]
    todo = [ImageJob(prompts[i], raw[i], refs=[raw[0]]) for i in range(1, len(raw)) if not fresh(raw[i], keys[i])]
    print(f"frames: {len(raw) - len(todo)} cached, {len(todo)} to make", flush=True)
    errors = run_jobs(todo, profile["providers"]["image"])
    for i in range(1, len(raw)):
        if raw[i].exists() and not any(e.startswith(raw[i].name) for e in errors):
            mark(raw[i], keys[i])
    if errors:
        raise SystemExit("frames failed:\n" + "\n".join(errors))

    for p in raw:
        crop_916(p, p.with_name(p.stem + "-916.png"))
    print(f"frames: {len(raw)} ready in {d}")
