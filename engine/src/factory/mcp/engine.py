"""HTTP client of the local engine; starts `factory serve` in the background when nothing answers."""

from __future__ import annotations

import contextlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from factory.core import DATA, ROOT

URL = "http://127.0.0.1:8790"
LOG = DATA / "engine.log"


class EngineError(RuntimeError):
    pass


def _send(method: str, path: str, body=None, timeout: float = 30):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        URL + path, data=data, method=method, headers={"Content-Type": "application/json", "X-Factory": "1"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        with contextlib.suppress(ValueError, AttributeError):
            detail = json.loads(detail).get("detail", detail)
        raise EngineError(f"{e.code}: {detail}") from None


def _alive() -> bool:
    try:
        return bool(_send("GET", "/api/health", timeout=2))
    except (OSError, EngineError):
        return False


def ensure() -> None:
    if _alive():
        return
    with open(LOG, "ab") as log:
        subprocess.Popen(
            [sys.executable, "-m", "factory", "serve"],
            cwd=ROOT,
            stdout=log,
            stderr=log,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    for _ in range(60):
        time.sleep(0.5)
        if _alive():
            return
    raise EngineError(f"the engine did not start; see {LOG}")


def call(method: str, path: str, body=None, timeout: float = 30, **query):
    ensure()
    if query:
        path += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
    return _send(method, path, body, timeout)


def file_json(slug: str, path: str):
    """A JSON file the engine serves from an episode folder, or None."""
    try:
        return call("GET", f"/files/episodes/{urllib.parse.quote(slug)}/{path}")
    except EngineError:
        return None
