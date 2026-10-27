"""Where things live. ROOT is the repository (a checkout, or the app's read-only resources): engine/, formats/,
render/. DATA is everything the engine writes: episodes, the machine profile, the queue, models, tools, music files,
keys. In a checkout DATA is data/ in the repository, ignored by git; the desktop app points it at the user's
application-data folder with CF_DATA."""

from __future__ import annotations

import os
import platform
from pathlib import Path

ROOT = Path(os.environ.get("CF_ROOT") or Path(__file__).resolve().parents[4])
ENGINE = ROOT / "engine"  # the Python project: pyproject.toml, uv.lock, src/
DATA = Path(os.environ.get("CF_DATA") or ROOT / "data")
FORMATS = ROOT / "formats"
EPISODES = DATA / "episodes"
PROFILE = DATA / "profile.yaml"
SECRETS = DATA / ".env"
MODELS = DATA / "models"
BIN = DATA / "tools" / "bin"


def platform_key() -> str:
    """Folder name for native binaries, e.g. macos-arm64 or windows-x64."""
    system = {"Darwin": "macos", "Windows": "windows"}.get(platform.system(), "linux")
    arch = {"arm64": "arm64", "aarch64": "arm64", "AMD64": "x64", "x86_64": "x64"}.get(
        platform.machine(), platform.machine()
    )
    return f"{system}-{arch}"


def tilde(path: Path) -> str:
    """A path as shown on screen: the home folder as ~, so a screenshot does not carry the user name."""
    home = Path.home()
    return f"~/{path.relative_to(home).as_posix()}" if path.is_relative_to(home) else str(path)
