"""`factory doctor`: look at the machine and write profile.yaml with a provider for every stage."""

from __future__ import annotations

import platform
import shutil
import subprocess

from factory.core import PROFILE, load_profile, platform_key, save_profile
from factory.core.profile import DEFAULT_VOICES, installed


def _gpu() -> str:
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        return "apple"
    if shutil.which("nvidia-smi"):
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True, check=False
        )
        if out.returncode == 0 and out.stdout.strip():
            return "nvidia"
    return "cpu"


def run() -> dict:
    """Detects the machine and writes profile.yaml. What the owner chose since (defaults, storage, image workers,
    voices) is kept: only what doctor detects is replaced."""
    prev = load_profile() if PROFILE.exists() else {}
    gpu = _gpu()
    tools = {name: shutil.which(name) for name in ("ffmpeg", "node", "npx")}
    image_workers = (prev.get("providers") or {}).get("image")
    if image_workers is None:
        from factory.providers import image

        image_workers = image.available()
    profile = {
        **prev,
        "platform": platform_key(),
        "gpu": gpu,
        "tools": tools,
        **installed(),
        "providers": {
            "image": image_workers,
            "depth": "onnx-coreml" if gpu == "apple" else "onnx-cuda" if gpu == "nvidia" else "onnx-cpu",
            "stt": "mlx-whisper" if gpu == "apple" else "faster-whisper",
            "render": "remotion",
        },
        # a re-run keeps the voices edited since
        "voices": {**DEFAULT_VOICES, **prev.get("voices", {})},
        "stt_model": "mlx-community/whisper-large-v3-turbo",
    }
    save_profile(profile)
    missing = [k for k, v in {**tools, "rife": profile["rife"], "depth_model": profile["depth_model"]}.items() if not v]
    print(
        f"profile.yaml: {profile['platform']}, gpu {gpu}, image workers {image_workers or 'none'}"
        + (f", missing: {', '.join(missing)}" if missing else "")
    )
    return profile
