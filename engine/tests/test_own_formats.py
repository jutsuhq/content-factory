from fastapi.testclient import TestClient

from factory.api import app
from factory.core import Episode, formats
from factory.stages import render
from factory.studio import formats as own
from factory.studio import storage


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(formats, "OWN_FORMATS", tmp_path / "formats")
    monkeypatch.setattr(own, "OWN_FORMATS", tmp_path / "formats")
    monkeypatch.setattr(storage, "EPISODES", tmp_path / "episodes")
    return TestClient(app, headers={"X-Factory": "1"})


def test_an_agent_copies_a_format_saves_its_own_and_it_works_at_once(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    shipped = formats.ids()[0]
    src = client.get(f"/api/formats/{shipped}/source").json()
    assert not src["own"] and "format.yaml" in src["files"] and "template/index.ts" in src["files"]

    files = {**src["files"], "format.yaml": src["files"]["format.yaml"].replace("title: ", "title: My ", 1)}
    r = client.put("/api/formats/a-show", json={"files": files})
    assert r.status_code == 200, r.text
    listed = {f["id"]: f for f in client.get("/api/formats").json()}
    assert listed["a-show"]["own"] and listed["a-show"]["title"].startswith("My ")
    assert formats.ids()[0] == shipped and client.get("/api/formats").json()[0]["id"] != "a-show"  # not the default
    assert "Example of a finished episode" in client.get("/api/formats/a-show/guide").json()["guide"]

    # a render bundles the episode's format's template alone: a copy keeps the composition id of its original
    monkeypatch.setattr(render, "TEMPLATES", tmp_path / "render-formats")
    ep = Episode("ep", tmp_path, {}, formats.load("a-show")["dir"])
    assert [d.name for d in render.gather_template(ep).iterdir()] == ["a-show"]

    # a broken version is refused and the working one stays
    broken = {**files, "beats.schema.json": "{ not json"}
    assert "beats.schema.json" in client.put("/api/formats/a-show", json={"files": broken}).json()["detail"]
    assert client.get("/api/formats/a-show/source").json()["files"]["beats.schema.json"] == files["beats.schema.json"]
    no_example = {k: v for k, v in files.items() if not k.startswith("examples/")}
    assert "examples/" in client.put("/api/formats/a-show", json={"files": no_example}).json()["detail"]

    assert client.delete("/api/formats/a-show").json() == {"ok": True}
    assert "a-show" not in formats.ids()


def test_shipped_formats_and_paths_outside_the_folder_are_refused(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    shipped = formats.ids()[0]
    assert "ships with the factory" in client.put(f"/api/formats/{shipped}", json={"files": {}}).json()["detail"]
    bad = client.put("/api/formats/evil", json={"files": {"../x.md": "x"}})
    assert bad.status_code == 400 and not (tmp_path / "x.md").exists()
    assert client.put("/api/formats/Bad_Id", json={"files": {}}).status_code == 400
    assert client.delete(f"/api/formats/{shipped}").status_code == 404
