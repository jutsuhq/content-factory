"""Worker pool: several workers run at once, a job goes to whichever is free, and a failed job is retried on another
worker."""

from __future__ import annotations

import queue
import time
from concurrent.futures import ThreadPoolExecutor

from factory.providers.image.fal import FalWorker
from factory.providers.image.gemini import GeminiWorker
from factory.providers.image.job import ImageJob
from factory.providers.image.openai import OpenAIWorker

# Add a backend: a class with `name`, `generate(job)` and `close()`, plus a line here.
WORKERS = {"openai": OpenAIWorker, "gemini": GeminiWorker, "fal": FalWorker}
try:  # optional local workers: a `private` package (ignored by git) with WORKERS, DEFAULTS and available()
    import factory.providers.image.private as private
except ModuleNotFoundError as e:
    if not (e.name or "").startswith("factory.providers.image.private"):
        raise
    private = None
PRIVATE: set[str] = set(private.WORKERS) if private else set()
if private:
    WORKERS |= private.WORKERS

# Errors that will not pass on a retry: out of quota for hours, the browser behind a worker is gone,
# or an API key that is wrong, out of credit or without billing.
FATAL = (
    "usage limit",
    "has been closed",
    "page closed",
    "not connected",
    "http 401",
    "http 403",
    "invalid_api_key",
    "incorrect api key",
    "api key not valid",
    "api_key_invalid",
    "insufficient_quota",
    "exceeded your current quota",
    "billing",
    "exhausted balance",
    "user is locked",
)


def _start(workers: dict[str, int], at_most: int) -> list:
    """`count` workers of each kind, no more than there are jobs; a worker that fails to start is skipped."""
    made = []
    for kind, count in workers.items():
        for n in range(1, min(count, at_most) + 1):
            try:
                made.append(WORKERS[kind](n))
            except Exception as e:  # one broken worker must not stop the others
                print(f"skip {kind}-{n}: {e}")
    if not made:
        raise SystemExit("no image workers: run `factory doctor`")
    return made


def run_jobs(jobs: list[ImageJob], workers: dict[str, int], attempts: int = 3) -> list[str]:
    """Run jobs on a pool of workers; returns error lines for jobs that failed every attempt."""
    if not jobs:
        return []
    made = _start(workers, len(jobs))
    pool: queue.Queue = queue.Queue()
    for w in made:
        pool.put(w)

    alive = {w.name for w in made}

    def one(job: ImageJob) -> str | None:
        errors: list[str] = []
        tried: set[str] = set()
        for _ in range(attempts):
            w = pool.get()
            while w.name in tried and alive - tried:  # a retry waits for a worker that has not tried this job yet
                pool.put(w)
                time.sleep(0.05)
                w = pool.get()
            tried.add(w.name)
            try:
                w.generate(job)
                print(f"{w.name}: {job.out.name}", flush=True)
                pool.put(w)
                return None
            except Exception as e:
                errors.append(" ".join(str(e).split())[:300])
                print(f"{w.name}: retry {job.out.name}: {errors[-1][:160]}", flush=True)
                if any(f in errors[-1].lower() for f in FATAL) and len(alive) > 1:
                    # retire the worker so it stops eating the other jobs' retries
                    alive.discard(w.name)
                    print(f"{w.name}: retired", flush=True)
                    continue
            pool.put(w)
        return f"{job.out.name}: " + " | ".join(errors)

    try:
        with ThreadPoolExecutor(max_workers=len(made)) as ex:
            return [e for e in ex.map(one, jobs) if e]
    finally:
        for w in made:
            w.close()
