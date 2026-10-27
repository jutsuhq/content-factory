import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from factory import stages
from factory.api import app
from factory.api.routes import episodes as routes
from factory.core import ROOT, Episode, formats
from factory.studio import compose, store


def test_every_format_declares_what_the_engine_reads():
    assert formats.default_id() in formats.ids()
    for fid in formats.ids():
        fmt = formats.load(fid)
        assert fmt["template"] and fmt["title"] and fmt["description"] and fmt["render_modes"]
        assert compose.guide("en", fid).strip()
        for mode, m in fmt["render_modes"].items():
            assert m["title"] and set(m["stages"]) <= set(stages.ORDER) and formats.style_ids(fmt, mode)
            b = compose.blank("x", 30, formats.style_ids(fmt, mode)[0], None, True, "en", mode, fid)
            assert b["format"] == fid and b["render_mode"] == mode
            assert not [p for p in compose.problems(b) if p.startswith("schema")]
            required = formats.keys(fmt, mode, "beat", "required")
            assert {f"beat 1 {k}" for k in required + ["vo"]} <= set(compose.missing(b))


def test_the_render_mode_decides_the_stages(tmp_path):
    fmt = formats.load()
    for mode, m in fmt["render_modes"].items():
        b = compose.blank("x", 30, formats.style_ids(fmt, mode)[0], None, False, "en", mode)
        (tmp_path / mode).mkdir()
        (tmp_path / mode / "beats.json").write_text(json.dumps(b), encoding="utf-8")
        ep = Episode.load(str(tmp_path / mode))
        assert stages.plan(ep) == [s for s in stages.ORDER if s in m["stages"] and s not in stages.VOICE]
        assert stages.plan(ep, ["render"]) == (["render"] if "render" in m["stages"] else [])
    with pytest.raises(ValueError):
        formats.load("no-such-format")


def test_episode_takes_its_format_and_old_scripts_fall_back_to_the_default(tmp_path):
    fmt = formats.load()
    beats = json.loads(formats.examples(fmt)[0].read_text(encoding="utf-8"))
    for name, b in (
        ("old", {k: v for k, v in beats.items() if k != "format"}),
        ("new", {**beats, "format": fmt["id"]}),
    ):
        (tmp_path / name).mkdir()
        (tmp_path / name / "beats.json").write_text(json.dumps(b), encoding="utf-8")
        ep = Episode.load(str(tmp_path / name))
        assert ep.format_dir == fmt["dir"] and ep.format["template"] == fmt["template"]


def test_compose_writes_the_format_and_the_api_lists_formats_and_styles(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EPISODES", tmp_path)
    monkeypatch.setattr(routes, "EPISODES", tmp_path)
    client = TestClient(app, headers={"X-Factory": "1"})
    listed = client.get("/api/formats").json()
    fid = listed[0]["id"]
    assert fid == formats.default_id() and listed[0]["render_modes"] and listed[0]["duration_seconds"]["max"]
    assert client.get("/api/styles", params={"format": fid}).json() == client.get("/api/styles").json()
    assert client.get("/api/styles", params={"format": "no-such-format"}).status_code == 404

    r = client.post("/api/compose", json={"topic": "The Moon", "format": fid, "language": "en"}).json()
    assert json.loads((tmp_path / r["slug"] / "beats.json").read_text(encoding="utf-8"))["format"] == fid
    assert client.post("/api/compose", json={"topic": "x", "format": "no-such-format"}).status_code == 400
    assert client.post("/api/compose", json={"topic": "x", "render_mode": "no-such-mode"}).status_code == 400


def test_no_format_is_hardwired_outside_its_folder():
    """The engine, the app and the shared renderer name no format; only formats/<id>/ may, template included."""
    try:
        files = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "engine/src", "app/src", "render/src"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    files = [f for f in files if (ROOT / f).exists()]
    for fid in formats.ids():
        names = {fid.lower(), fid.replace("-", "").lower(), formats.load(fid)["template"].lower()}
        hits = [
            f for f in files for n in names if n in Path(ROOT / f).read_text(encoding="utf-8", errors="ignore").lower()
        ]
        assert not hits, f"{fid} named in {hits}"
