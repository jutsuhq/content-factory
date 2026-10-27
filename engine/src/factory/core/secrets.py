"""API keys, in DATA/.env (never in profile.yaml, never sent to the app): KEY=value lines, read on every call so a
key saved in Settings works at once."""

from __future__ import annotations

import os

from factory.core.paths import SECRETS


def read() -> dict[str, str]:
    if not SECRETS.exists():
        return {}
    pairs = (line.split("=", 1) for line in SECRETS.read_text(encoding="utf-8").splitlines() if "=" in line)
    return {k.strip(): v.strip() for k, v in pairs if not k.strip().startswith("#")}


def get(name: str) -> str | None:
    """The environment wins over the file, so CI and shells can pass keys without touching it."""
    return os.environ.get(name) or read().get(name) or None


def put(**values: str | None) -> None:
    """Sets keys; an empty string or None removes one."""
    env = read()
    for k, v in values.items():
        if v:
            env[k] = v
        else:
            env.pop(k, None)
    SECRETS.parent.mkdir(parents=True, exist_ok=True)
    SECRETS.write_text("".join(f"{k}={v}\n" for k, v in env.items()), encoding="utf-8")
    if os.name != "nt":
        SECRETS.chmod(0o600)
