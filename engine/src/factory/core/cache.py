"""Stage cache: an output is fresh when a `<name>.key` file next to it holds the hash of the inputs it was made from."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def digest(*items) -> str:
    """Stable hash of the inputs of one stage step: strings, dicts, numbers and file paths (by content)."""
    h = hashlib.sha256()
    for item in items:
        if isinstance(item, Path):
            h.update(item.read_bytes())
        else:
            h.update(json.dumps(item, sort_keys=True, ensure_ascii=False).encode())
    return h.hexdigest()[:16]


def fresh(out: Path, key: str) -> bool:
    """True when `out` was already made from inputs with this key."""
    stamp = out.with_name(out.name + ".key")
    return out.exists() and stamp.exists() and stamp.read_text() == key


def mark(out: Path, key: str) -> None:
    out.with_name(out.name + ".key").write_text(key)
