"""The desktop app ships the engine as the resources listed in tauri.conf.json and builds it on first launch, so a
file left out there breaks every fresh install. These tests assemble that bundle and build the engine from it."""

import json
import shutil
import subprocess

import pytest

from factory.core import ROOT

CONF = ROOT / "app" / "src-tauri" / "tauri.conf.json"


def _bundle(dest):
    resources = json.loads(CONF.read_text(encoding="utf-8"))["bundle"]["resources"]
    for src, target in resources.items():
        path = (CONF.parent / src).resolve()
        assert path.exists(), f"tauri.conf.json bundles {src}, which does not exist"
        out = dest / target
        if path.is_dir():
            ignore = shutil.ignore_patterns("__pycache__", "private", "node_modules")
            shutil.copytree(path, out, dirs_exist_ok=True, ignore=ignore)
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, out)
    return dest / "repo"


def test_the_bundled_engine_builds(tmp_path):
    if not shutil.which("uv"):
        pytest.skip("uv not installed")
    repo = _bundle(tmp_path / "Resources")
    r = subprocess.run(
        ["uv", "build", "--wheel", "--quiet", "--out-dir", str(tmp_path / "dist"), str(repo / "engine")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr[-1500:]


def test_the_bundle_carries_formats_and_the_renderer(tmp_path):
    repo = _bundle(tmp_path / "Resources")
    assert (repo / "engine" / "uv.lock").is_file()
    assert any((repo / "formats").glob("*/format.yaml"))
    assert (repo / "skills" / "make-video" / "SKILL.md").is_file()  # the MCP server serves it
    for name in ("package.json", "package-lock.json", "tsconfig.json", "remotion.config.ts", "src/index.ts"):
        assert (repo / "render" / name).is_file(), name
