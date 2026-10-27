from fastapi.testclient import TestClient

from factory.api import app
from factory.api.routes import episodes as routes
from factory.core import Episode, projects
from factory.stages import frames
from factory.studio import storage, store

PNG = b"\x89PNG\r\n\x1a\n"


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(projects, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(store, "EPISODES", tmp_path / "episodes")
    monkeypatch.setattr(routes, "EPISODES", tmp_path / "episodes")
    monkeypatch.setattr(storage, "EPISODES", tmp_path / "episodes")
    return TestClient(app, headers={"X-Factory": "1"})


def test_a_video_of_a_project_takes_the_variant_settings_and_its_cast_reaches_every_frame(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    p = client.post("/api/projects", json={"name": "Toon Kids", "platform": "tiktok", "handle": "@toon"}).json()
    assert p["id"] == "toon-kids" and [v["name"] for v in p["variants"]] == ["Main"]  # one variant from the defaults

    p["cast"] = [{"name": "Boy", "looks": "a ten-year-old boy, red cap"}, {"name": "Dog", "looks": "a small beagle"}]
    p["variants"].append({"name": "Russian shorts", "language": "ru", "duration": 30, "voice": False, "cast": ["boy"]})
    p = client.put("/api/projects/toon-kids", json=p).json()
    assert [c["id"] for c in p["cast"]] == ["boy", "dog"] and p["variants"][1]["id"] == "russian-shorts"
    p = client.post("/api/projects/toon-kids/cast/boy/refs", files={"file": ("face.png", PNG)}).json()
    assert p["cast"][0]["refs"] == ["projects/toon-kids/cast/boy/01.png"]
    assert client.post("/api/projects/toon-kids/cast/boy/refs", files={"file": ("a.txt", b"x")}).status_code == 400

    r = client.post("/api/compose", json={"topic": "first day", "project": "toon-kids", "variant": "russian-shorts"})
    slug = r.json()["slug"]
    ep = client.get(f"/api/episodes/{slug}").json()
    assert (ep["project"], ep["variant"], ep["language"]) == ("toon-kids", "russian-shorts", "ru")
    assert ep["beats"]["cast"] == ["boy"] and ep["beats"]["voice"] is False
    assert [e["slug"] for e in client.get("/api/episodes", params={"project": "toon-kids"}).json()] == [slug]
    assert client.get("/api/episodes", params={"project": "other"}).json() == []
    bad = {"topic": "x", "project": "toon-kids", "cast": ["cat"]}
    assert client.post("/api/compose", json=bad).status_code == 400

    text, files = frames._cast(Episode(slug, tmp_path, ep["beats"], tmp_path))
    assert "Boy: a ten-year-old boy, red cap" in text and "Dog" not in text
    assert [f.name for f in files] == ["01.png"]


def test_dropping_a_character_drops_its_refs_and_a_removed_project_goes_to_trash(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    p = client.post("/api/projects", json={"name": "Space", "cast": [{"name": "Robot"}]}).json()
    client.post("/api/projects/space/cast/robot/refs", files={"file": ("r.jpg", PNG)})
    p["cast"] = []
    assert client.put("/api/projects/space", json=p).json()["cast"] == []
    assert not (tmp_path / "projects/space/cast/robot").exists()
    assert client.put("/api/projects/space", json={**p, "name": " "}).status_code == 400

    assert client.delete("/api/projects/space").json() == {"ok": True}
    assert client.get("/api/projects").json() == []
    assert [d.name.startswith("project-space-") for d in (tmp_path / "episodes/.trash").iterdir()] == [True]
