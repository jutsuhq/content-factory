import sqlite3
import threading

from factory import jobs


def test_start_drops_old_kinds_reruns_light_jobs_and_clear_keeps_active(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "DB", tmp_path / "jobs.db")
    jobs.init()
    with sqlite3.connect(jobs.DB) as con:
        for kind, status in (
            ("translate", "failed"),
            ("style_preview", "queued"),
            ("generate", "done"),
            ("generate", "queued"),
        ):
            con.execute(
                "insert into jobs (kind, status, params, progress, log, created) values (?, ?, '{}', 0, '', 0)",
                (kind, status),
            )
    ran = threading.Event()
    monkeypatch.setattr(
        jobs, "handlers", {"style_preview": lambda job, log: ran.set(), "generate": lambda job, log: None}
    )
    monkeypatch.setattr(jobs, "_heavy_worker", lambda: None)

    jobs.start()
    assert ran.wait(2) and jobs.wait_finished(2, 2)["status"] == "done"  # left queued when the app quit, ran again
    assert "translate" not in {j["kind"] for j in jobs.list_jobs()}

    assert jobs.clear_finished() >= 2
    assert [(j["kind"], j["status"]) for j in jobs.list_jobs()] == [("generate", "queued")]
