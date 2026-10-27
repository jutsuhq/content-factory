"""transitions: RIFE in-betweens for every pair of neighbouring frames, one folder per pair."""

from __future__ import annotations

import itertools
import shutil
import subprocess
import tempfile
from pathlib import Path

from factory.core import Episode, digest, fresh, mark

FRAMES_PER_PAIR = 48  # 2 s at 24 fps; the render stretches them over the transition length
MODEL = "rife-v4.6"
FORMAT = "jpg"  # Remotion copies the public dir before rendering: JPG keeps it ~5x smaller than PNG


def run(ep: Episode, profile: dict) -> None:
    rife = Path(profile["rife"])
    frames = sorted(ep.work("frames").glob("[0-9][0-9]-916.png"))
    made = 0
    for a, b in itertools.pairwise(frames):
        out = ep.work("rife", f"{a.stem[:2]}-{b.stem[:2]}")
        done = out / "done"
        key = digest(a, b, FRAMES_PER_PAIR, MODEL, FORMAT)
        if fresh(done, key):
            continue
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp)
            shutil.copyfile(a, src / "00000001.png")
            shutil.copyfile(b, src / "00000002.png")
            for old in [*out.glob("*.png"), *out.glob("*.jpg")]:
                old.unlink()
            subprocess.run(
                [
                    str(rife),
                    "-i",
                    str(src),
                    "-o",
                    str(out),
                    "-m",
                    str(rife.parent / MODEL),
                    "-n",
                    str(FRAMES_PER_PAIR),
                    "-f",
                    FORMAT,
                ],
                check=True,
                capture_output=True,
            )
        done.write_text("")
        mark(done, key)
        made += 1
    print(f"transitions: {len(frames) - 1 - made} cached, {made} made")
