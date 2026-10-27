"""Import CC0 music from OpenGameArt: `factory music fetch <page-slug> --moods calm,space`.

The page must offer CC0 (other licenses need attribution or forbid reuse, so pages without it are refused). The track is
converted to AAC and levelled to LEVEL LUFS, so the mix gain in voice.audio fits every track."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from factory.music import library

SITE = "https://opengameart.org"
LEVEL = -20.0
MAX_BYTES = 60_000_000


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "content-factory/0.1 (+local music import)"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read(MAX_BYTES + 1)


def fetch(slug: str, moods: list[str], default: bool = False) -> dict:
    page = _get(f"{SITE}/content/{slug}").decode("utf-8", "replace")
    licenses = re.findall(r"license-name'>([^<]+)<", page)
    if "CC0" not in licenses:  # a page under several licenses lets the user pick any of them, CC0 included
        raise RuntimeError(f"{slug}: license is {', '.join(licenses) or 'unknown'}, only CC0 is imported")
    files = [
        f
        for f in re.findall(
            r"""href=["'](https://opengameart\.org/sites/default/files/[^"']+\.(?:ogg|mp3|wav|flac))["']""", page
        )
        if "/audio_preview/" not in f
    ]
    # some pages attach no file and only feed the original to their player
    files = files or [f for f in re.findall(r"data-ogg-url='([^']+)'", page) if "/audio_preview/" not in f]
    if not files:
        raise RuntimeError(f"{slug}: no audio file on the page")
    found = re.search(r"<title>([^|<]+)", page)
    title = found.group(1).strip() if found else slug
    author = (re.search(r'href="/users/([^"]+)"', page) or [None, "unknown"])[1]
    data = _get(files[0])
    if len(data) > MAX_BYTES:
        raise RuntimeError(f"{slug}: file over {MAX_BYTES // 1_000_000} MB")
    library.DIR.mkdir(parents=True, exist_ok=True)
    out = library.DIR / f"{slug}.m4a"
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / Path(files[0]).name
        src.write_bytes(data)
        subprocess.run(
            [
                shutil.which("ffmpeg") or "ffmpeg",
                "-hide_banner",
                "-y",
                "-i",
                str(src),
                "-vn",
                "-af",
                f"loudnorm=I={LEVEL}:TP=-2:LRA=11",
                "-ar",
                "48000",
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                str(out),
            ],
            check=True,
            capture_output=True,
        )
    track = {
        "id": slug,
        "file": out.name,
        "title": title,
        "author": author,
        "source": f"{SITE}/content/{slug}",
        "license": "CC0",
        "moods": moods,
        **({"default": True} if default else {}),
    }
    items = [t for t in library.tracks() if t["id"] != slug] + [track]
    library.save(items)
    return track
