"""First-run setup: what the engine needs on this machine, whether it is there, and installing what it can fetch
itself. System tools (ffmpeg, Node.js) come with an install command instead, since they belong to the system."""

from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import stat
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from factory.core import BIN, ENGINE, MODELS, ROOT, platform_key

SYSTEM = platform.system()
RIFE_VERSION = "20221029"
RIFE_ASSET = {"Darwin": "macos", "Windows": "windows"}.get(SYSTEM, "ubuntu")
RIFE_URL = f"https://github.com/nihui/rife-ncnn-vulkan/releases/download/{RIFE_VERSION}/rife-ncnn-vulkan-{RIFE_VERSION}-{RIFE_ASSET}.zip"
DEPTH_URL = "https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx"  # Apache-2.0
DEPTH = MODELS / "depth" / "da2-small.onnx"

HINTS = {
    "ffmpeg": {
        "Darwin": "brew install ffmpeg",
        "Windows": "winget install Gyan.FFmpeg",
        "Linux": "sudo apt install ffmpeg",
    },
    "node": {
        "Darwin": "brew install node",
        "Windows": "winget install OpenJS.NodeJS.LTS",
        "Linux": "sudo apt install nodejs npm",
    },
}


def _render_dir() -> Path:
    from factory.stages.render import RENDER

    return RENDER


def _rife() -> Path | None:
    exe = "rife-ncnn-vulkan.exe" if SYSTEM == "Windows" else "rife-ncnn-vulkan"
    hits = sorted((BIN / platform_key()).rglob(exe))
    return hits[0] if hits else None


def components() -> list[dict]:
    """Each piece with `ok`, a line of detail, and either `install` (the engine fetches it) or `command` (the user
    runs it once)."""
    from factory.music import library

    tracks = len(library.tracks())
    render = _render_dir()
    out = [
        {
            "id": "ffmpeg",
            "title": "FFmpeg",
            "detail": "cuts, mixes and measures audio and video",
            "ok": bool(shutil.which("ffmpeg") and shutil.which("ffprobe")),
            "command": HINTS["ffmpeg"].get(SYSTEM),
        },
        {
            "id": "node",
            "title": "Node.js",
            "detail": "runs the video renderer (Remotion)",
            "ok": bool(shutil.which("node") and shutil.which("npx")),
            "command": HINTS["node"].get(SYSTEM),
        },
        {
            "id": "render",
            "title": "Video renderer",
            "detail": "Remotion and its packages, about 1 GB; Remotion has its own license",
            "ok": (render / "node_modules" / "remotion").exists(),
            "install": True,
            "needs": "node",
        },
        {
            "id": "rife",
            "title": "Transitions",
            "detail": "RIFE frame interpolation, about 30 MB",
            "ok": _rife() is not None,
            "install": True,
        },
        {
            "id": "depth",
            "title": "Depth model",
            "detail": "Depth Anything V2 small for the parallax motion, 99 MB",
            "ok": DEPTH.exists(),
            "install": True,
        },
        {
            "id": "music",
            "title": "Music",
            "detail": f"CC0 starter tracks from OpenGameArt ({tracks} installed)",
            "ok": tracks > 0,
            "install": library.STARTER.exists(),
            "needs": "ffmpeg",
        },
        {
            "id": "vosk",
            "title": "Russian voice",
            "detail": "Vosk-TTS with RUAccent stress, about 1 GB with its models",
            "ok": importlib.util.find_spec("vosk_tts") is not None,
            "install": True,
            "optional": True,
        },
    ]
    return out


def _download(url: str, out: Path, log) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "content-factory-setup"})
    tmp = out.with_name(out.name + ".part")
    with urllib.request.urlopen(req, timeout=60) as r, tmp.open("wb") as f:
        total, done, step = int(r.headers.get("content-length") or 0), 0, 0
        while chunk := r.read(1 << 20):
            f.write(chunk)
            done += len(chunk)
            if total and done * 10 // total > step:
                step = done * 10 // total
                log(f"{out.name}: {step * 10}%")
    tmp.replace(out)


def _install_rife(log) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        z = Path(tmp) / "rife.zip"
        _download(RIFE_URL, z, log)
        with zipfile.ZipFile(z) as zf:
            zf.extractall(BIN / platform_key() / "dl")
    exe = _rife()
    if not exe:
        raise RuntimeError("RIFE archive had no executable")
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _install_depth(log) -> None:
    _download(DEPTH_URL, DEPTH, log)


def _run(cmd: list[str], log, **kw) -> None:
    log(f"{Path(cmd[0]).name} {' '.join(cmd[1:])}")
    r = subprocess.run(cmd, capture_output=True, text=True, check=False, **kw)
    if r.returncode:
        raise RuntimeError(f"{Path(cmd[0]).name} failed: {(r.stderr or r.stdout)[-300:]}")


def _install_render(log) -> None:
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("Node.js is not installed")
    render = _render_dir()
    if render != ROOT / "render":  # the app's copy: refresh the template, keep node_modules
        ignore = shutil.ignore_patterns("node_modules", "out")
        shutil.copytree(ROOT / "render", render, dirs_exist_ok=True, ignore=ignore)
    log("npm install takes a few minutes")
    _run([npm, "install", "--no-audit", "--no-fund"], log, cwd=render)


def _install_music(log) -> None:
    import yaml

    from factory.music import fetch, library

    for item in yaml.safe_load(library.STARTER.read_text(encoding="utf-8")):
        try:
            fetch.fetch(item["slug"], item.get("moods", []), item.get("default", False))
            log(f"music: {item['slug']}")
        except Exception as e:  # one page gone from the site must not stop the rest
            log(f"music: skip {item['slug']}: {e}")


def _install_vosk(log) -> None:
    # into the environment the engine runs in; --inexact keeps the other extras it was started with
    uv = os.environ.get("UV") or shutil.which("uv")
    if not uv:
        raise RuntimeError("uv not found")
    _run([uv, "sync", "--inexact", "--frozen", "--extra", "vosk", "--project", str(ENGINE)], log)
    importlib.invalidate_caches()


INSTALLERS = {
    "rife": _install_rife,
    "depth": _install_depth,
    "render": _install_render,
    "music": _install_music,
    "vosk": _install_vosk,
}


def install(component: str, log=print) -> None:
    if component not in INSTALLERS:
        raise ValueError(f"cannot install {component}; installable: {', '.join(INSTALLERS)}")
    INSTALLERS[component](log)
    log(f"{component}: done")


def missing() -> list[str]:
    """Installable components that are not there yet, in install order; optional ones only when asked by name."""
    return [c["id"] for c in components() if not c["ok"] and c.get("install") and not c.get("optional")]
