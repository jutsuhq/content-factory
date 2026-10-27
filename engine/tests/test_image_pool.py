"""The worker pool: a failed image is retried on another worker, and a worker whose error will not pass on a retry
(no quota, a bad key) is retired so it stops eating the other jobs' attempts."""

import pytest

from factory.providers.image import pool
from factory.providers.image.job import ImageJob


def kinds(**behaviour):
    """Worker classes by name; each generates or raises as told, and records what it made."""
    made: dict[str, list[str]] = {}

    def worker(kind, fail):
        class W:
            def __init__(self, n):
                self.name = f"{kind}-{n}"

            def generate(self, job):
                if fail:
                    raise RuntimeError(fail)
                made.setdefault(kind, []).append(job.out.name)

            def close(self):
                pass

        return W

    return {k: worker(k, fail) for k, fail in behaviour.items()}, made


def test_a_failed_job_is_retried_on_another_worker(monkeypatch, tmp_path):
    workers, made = kinds(bad="HTTP 500 try later", good=None)
    monkeypatch.setattr(pool, "WORKERS", workers)
    jobs = [ImageJob("p", tmp_path / f"{i}.png") for i in range(3)]
    assert pool.run_jobs(jobs, {"bad": 1, "good": 1}) == []
    assert sorted(made["good"]) == ["0.png", "1.png", "2.png"]


def test_a_job_that_fails_everywhere_comes_back_as_an_error(monkeypatch, tmp_path):
    workers, _ = kinds(bad="HTTP 500 try later")
    monkeypatch.setattr(pool, "WORKERS", workers)
    errors = pool.run_jobs([ImageJob("p", tmp_path / "a.png")], {"bad": 1}, attempts=2)
    assert errors == ["a.png: HTTP 500 try later | HTTP 500 try later"]


def test_a_worker_with_a_fatal_error_is_retired(monkeypatch, tmp_path, capsys):
    workers, made = kinds(broke="insufficient_quota", good=None)
    monkeypatch.setattr(pool, "WORKERS", workers)
    jobs = [ImageJob("p", tmp_path / f"{i}.png") for i in range(4)]
    assert pool.run_jobs(jobs, {"broke": 1, "good": 1}) == []
    assert len(made["good"]) == 4
    assert capsys.readouterr().out.count("broke-1: retired") == 1


def test_no_worker_that_starts_is_a_clear_stop(monkeypatch, tmp_path):
    class Broken:
        def __init__(self, n):
            raise RuntimeError("no key")

    monkeypatch.setattr(pool, "WORKERS", {"x": Broken})
    with pytest.raises(SystemExit, match="no image workers"):
        pool.run_jobs([ImageJob("p", tmp_path / "a.png")], {"x": 1})
