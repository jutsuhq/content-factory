"""The command line is a client of the same commands as the MCP server: arguments map onto them, and a terminal
waits for the job instead of handing the waiting back."""

import json
import sys

import pytest

from factory import cli
from factory.mcp import server


def test_json_arguments_come_inline_from_a_file_or_from_stdin(tmp_path, monkeypatch):
    f = tmp_path / "beats.json"
    f.write_text('{"hook": "from a file"}', encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO('{"hook": "from stdin"}'))
    assert cli._json('{"hook": "inline"}') == {"hook": "inline"}
    assert cli._json(str(f)) == {"hook": "from a file"}
    assert cli._json("-") == {"hook": "from stdin"}
    assert cli._json(None) is None


def test_follow_keeps_waiting_until_the_job_reply_stops_asking(monkeypatch):
    replies = iter(["job 7 · running 50%\ncall job(7) again to keep waiting", "job 7 · done\nvideo: out.mp4"])
    monkeypatch.setattr(server, "job", lambda job_id: next(replies))
    assert cli._follow("job 7 · queued\ncall job(7) again to keep waiting") == "job 7 · done\nvideo: out.mp4"


def run(monkeypatch, capsys, *argv) -> str:
    monkeypatch.setattr(sys, "argv", ["factory", *argv])
    cli.main()
    return capsys.readouterr().out.strip()


def test_create_passes_every_option_to_the_shared_command(monkeypatch, capsys, tmp_path):
    seen = {}
    monkeypatch.setattr(server, "create", lambda *a: seen.setdefault("args", a) and "created")
    script = tmp_path / "s.json"
    script.write_text(json.dumps({"hook": "h"}), encoding="utf-8")
    out = run(
        monkeypatch,
        capsys,
        "create",
        "Moon",
        "--script",
        str(script),
        "--format",
        "fmt",
        "--no-voice",
        "--duration",
        "40",
        "--project",
        "kids",
        "--cast",
        "boy,dog",
    )
    assert out == "created"
    topic, beats, language, duration, style, voice, series, style_prompt, fmt, project, variant, cast = seen["args"]
    assert (topic, beats, duration, voice, fmt) == ("Moon", {"hook": "h"}, 40, False, "fmt")
    assert (project, variant, cast) == ("kids", None, ["boy", "dog"])
    assert (language, style, series, style_prompt) == (None, None, None, None)


def test_run_waits_for_the_job_unless_told_not_to(monkeypatch, capsys):
    monkeypatch.setattr(server, "run", lambda *a: "job 3 · queued\ncall job(3) again to keep waiting")
    monkeypatch.setattr(server, "job", lambda job_id: "job 3 · done")
    assert run(monkeypatch, capsys, "run", "moon", "rebuild", "--stages", "render,qa") == "job 3 · done"
    assert "call job(3) again" in run(monkeypatch, capsys, "run", "moon", "approve", "--no-wait")


def test_unknown_action_is_refused_by_the_parser(monkeypatch, capsys):
    with pytest.raises(SystemExit):
        run(monkeypatch, capsys, "run", "moon", "publish")
