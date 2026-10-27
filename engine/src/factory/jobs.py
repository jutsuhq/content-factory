"""Job queue for the app. Heavy jobs (frames, depth, RIFE, TTS, render) run one at a time in a worker thread,
each stage as a `factory stage <episode> <stage>` subprocess so it can be cancelled; light jobs (scripts, ideas,
style previews) run at once in their own threads. Jobs live in SQLite and survive a restart."""

from __future__ import annotations

import json
import os
import re
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import traceback
from collections.abc import Callable

from factory.core import DATA, ROOT

DB = DATA / "factory.db"
HEAVY = {"generate", "stages"}

_lock = threading.Lock()
_changed = threading.Condition()
_version = 0
_procs: dict[int, subprocess.Popen] = {}
_cancelled: set[int] = set()
_wake = threading.Event()
handlers: dict[str, Callable[[dict, Callable[[str], None]], None]] = {}


def _db() -> sqlite3.Connection:
    con = sqlite3.connect(DB, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def init() -> None:
    with _lock, _db() as con:
        con.execute(
            "create table if not exists jobs (id integer primary key, kind text, slug text, params text, status text,"
            " stage text, progress real, log text, error text, created real, started real, finished real)"
        )
        # a job that was running when the app quit is gone: mark it so the owner can restart it
        con.execute("update jobs set status='failed', error='stopped: the app was closed' where status='running'")


def _notify() -> None:
    global _version  # noqa: PLW0603  a counter guarded by _changed
    with _changed:
        _version += 1
        _changed.notify_all()


def wait_change(seen: int, timeout: float = 15) -> int:
    with _changed:
        _changed.wait_for(lambda: _version != seen, timeout)
        return _version


def wait_finished(job_id: int, timeout: float) -> dict | None:
    """The job once it is done, failed or cancelled, or as it stands when the timeout runs out."""
    deadline = time.monotonic() + timeout
    seen = _version
    while (job := get(job_id)) and job["status"] in ("queued", "running") and (left := deadline - time.monotonic()) > 0:
        seen = wait_change(seen, min(left, 15))
    return job


def _row(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["params"] = json.loads(d["params"] or "{}")
    return d


def list_jobs(limit: int = 100) -> list[dict]:
    with _lock, _db() as con:
        return [_row(r) for r in con.execute("select * from jobs order by id desc limit ?", (limit,))]


def get(job_id: int) -> dict | None:
    with _lock, _db() as con:
        r = con.execute("select * from jobs where id=?", (job_id,)).fetchone()
        return _row(r) if r else None


def _update(job_id: int, **fields) -> None:
    with _lock, _db() as con:
        con.execute(f"update jobs set {', '.join(f'{k}=?' for k in fields)} where id=?", (*fields.values(), job_id))
    _notify()


def update_params(job_id: int, **params) -> None:
    """Add results to a job's params, e.g. the slug a translation created, for the app to follow."""
    job = get(job_id)
    if job:
        _update(job_id, params=json.dumps({**job["params"], **params}, ensure_ascii=False))


def submit(kind: str, slug: str | None = None, **params) -> int:
    with _lock, _db() as con:
        cur = con.execute(
            "insert into jobs (kind, slug, params, status, progress, log, created)"
            " values (?, ?, ?, 'queued', 0, '', ?)",
            (kind, slug, json.dumps(params, ensure_ascii=False), time.time()),
        )
        job_id = int(cur.lastrowid or 0)
    _notify()
    if kind in HEAVY:
        _wake.set()
    else:
        threading.Thread(target=_run, args=(job_id,), daemon=True).start()
    return job_id


def cancel(job_id: int) -> None:
    _cancelled.add(job_id)
    proc = _procs.get(job_id)
    if proc and proc.poll() is None:
        if os.name == "nt":
            proc.terminate()
        else:
            os.killpg(proc.pid, signal.SIGTERM)
    job = get(job_id)
    if job and job["status"] == "queued":
        _update(job_id, status="cancelled", finished=time.time())


def _append_log(job_id: int, line: str) -> None:
    with _lock, _db() as con:
        r = con.execute("select log from jobs where id=?", (job_id,)).fetchone()
        log = ((r["log"] if r else "") + line + "\n")[-8000:]
        con.execute("update jobs set log=? where id=?", (log, job_id))
    _notify()


def run_stages(job_id: int, slug: str, stages: list[str], log: Callable[[str], None]) -> None:
    """Run stages as subprocesses; progress moves through stages and, for frames, per finished image."""
    total_frames = None
    for k, stage in enumerate(stages):
        if job_id in _cancelled:
            raise InterruptedError
        _update(job_id, stage=stage, progress=k / len(stages))
        cmd = [sys.executable, "-m", "factory", "stage", slug, stage]
        kw: dict = (
            {"start_new_session": True} if os.name != "nt" else {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        )
        proc = subprocess.Popen(
            cmd,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            **kw,
        )
        _procs[job_id] = proc
        done_frames = total_frames = 0
        tail: list[str] = []
        for raw in proc.stdout:  # type: ignore[union-attr]
            line = raw.rstrip()
            if not line or "Context leak" in line:
                continue
            tail = [*tail, line][-30:]
            log(line)
            m = re.match(r"frames: (\d+) cached, (\d+) to make", line)
            if m:
                total_frames = int(m.group(2)) + 1
            if stage == "frames" and re.match(r"[a-z]+-\d+: \d+\.png$", line):
                done_frames += 1
                frac = done_frames / max(total_frames, 1)
                _update(job_id, progress=(k + min(frac, 1)) / len(stages))
        proc.wait()
        _procs.pop(job_id, None)
        if job_id in _cancelled:
            raise InterruptedError
        if proc.returncode != 0:
            raise RuntimeError(
                next(
                    (t for t in reversed(tail) if "Error" in t or "error" in t or "failed" in t),
                    tail[-1] if tail else f"{stage} failed",
                )
            )


def _run(job_id: int) -> None:
    job = get(job_id)
    if not job or job["status"] == "cancelled":
        return
    _update(job_id, status="running", started=time.time())
    try:
        handlers[job["kind"]](job, lambda line: _append_log(job_id, line))
        _update(job_id, status="done", progress=1, finished=time.time())
    except InterruptedError:
        _update(job_id, status="cancelled", finished=time.time())
    except Exception as e:  # the job fails, the app keeps running
        _append_log(job_id, traceback.format_exc()[-2000:])
        _update(job_id, status="failed", error=str(e)[:500], finished=time.time())
        on_fail = handlers.get(f"{job['kind']}:failed")
        if on_fail:
            on_fail(job, lambda line: None)


def _heavy_worker() -> None:
    while True:
        _wake.wait(5)
        _wake.clear()
        while True:
            with _lock, _db() as con:
                placeholders = ",".join("?" * len(HEAVY))
                r = con.execute(
                    f"select id from jobs where status='queued' and kind in ({placeholders}) order by id limit 1",
                    tuple(HEAVY),
                ).fetchone()
            if not r:
                break
            _run(r["id"])


def clear_finished() -> int:
    """Removes done, failed and cancelled jobs from the list; answers how many."""
    with _lock, _db() as con:
        n = con.execute("delete from jobs where status in ('done', 'failed', 'cancelled')").rowcount
    _notify()
    return n


def start() -> None:
    """Call after `handlers` is filled: jobs of kinds the app no longer has are dropped, light jobs left queued when
    the app quit run again, heavy ones go to the worker."""
    init()
    with _lock, _db() as con:
        known = [k for k in handlers if ":" not in k]
        if known:  # never prune before the app registered its handlers
            con.execute(f"delete from jobs where kind not in ({','.join('?' * len(known))})", known)
        waiting = [
            r["id"] for r in con.execute("select id, kind from jobs where status='queued'") if r["kind"] not in HEAVY
        ]
    for job_id in waiting:
        threading.Thread(target=_run, args=(job_id,), daemon=True).start()
    threading.Thread(target=_heavy_worker, daemon=True).start()
    _wake.set()
