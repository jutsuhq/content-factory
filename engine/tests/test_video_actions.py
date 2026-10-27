from fastapi.testclient import TestClient

from factory.api import app
from factory.api.routes import episodes as routes
from factory.studio import storage, store


def test_accept_keeps_the_caption_and_desktop_actions_get_the_video(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EPISODES", tmp_path)
    monkeypatch.setattr(routes, "EPISODES", tmp_path)
    monkeypatch.setattr(storage, "EPISODES", tmp_path)
    settings = {"export_dir": str(tmp_path / "export"), "copy_on_accept": True, "clean_after_accept": True}
    monkeypatch.setattr(routes, "storage", lambda: settings)
    monkeypatch.setattr(storage, "storage", lambda: settings)
    called = []
    monkeypatch.setitem(routes.DESKTOP, "copy", called.append)
    (tmp_path / "moon").mkdir()
    client = TestClient(app, headers={"X-Factory": "1"})

    assert client.post("/api/episodes/moon/video/copy").status_code == 404  # nothing rendered yet
    (tmp_path / "moon" / "out").mkdir()
    (tmp_path / "moon" / "out" / "moon.mp4").write_bytes(b"mp4")
    assert client.post("/api/episodes/moon/video/copy").json() == {"ok": True}
    assert called == [tmp_path / "moon" / "out" / "moon.mp4"]
    assert client.post("/api/episodes/moon/video/delete").status_code == 422

    rife = tmp_path / "moon" / "work" / "public" / "rife" / "01-02"
    rife.mkdir(parents=True)
    (rife / "0001.png").write_bytes(b"png")
    store.save_meta("moon", title="Moon gone")

    r = client.post("/api/episodes/moon/accept", json={"caption": "Day 1 #fyp"}).json()
    assert r["video"].endswith("moon.mp4") and r["exported"] == str(tmp_path / "export" / "moon-gone.mp4")
    assert store.meta("moon")["status"] == "done" and store.meta("moon")["caption"] == "Day 1 #fyp"
    assert not rife.exists()  # clean_after_accept
    client.post("/api/episodes/moon/accept", json={"caption": "edited"})  # saving the caption again copies nothing
    assert [f.name for f in (tmp_path / "export").iterdir()] == ["moon-gone.mp4"]


def test_export_never_overwrites_and_cache_only_goes_for_settled_episodes(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EPISODES", tmp_path)
    monkeypatch.setattr(storage, "EPISODES", tmp_path)
    monkeypatch.setattr(storage, "storage", lambda: {"export_dir": str(tmp_path / "export")})
    for slug, status in (("a", "done"), ("b", "generating")):
        (tmp_path / slug / "out").mkdir(parents=True)
        (tmp_path / slug / "out" / f"{slug}.mp4").write_bytes(b"x" * 10)
        (tmp_path / slug / "work" / "public" / "rife").mkdir(parents=True)
        (tmp_path / slug / "work" / "public" / "rife" / "f.png").write_bytes(b"y" * 100)
        store.save_meta(slug, status=status, title="Same title")
    (tmp_path / ".trash" / "old").mkdir(parents=True)
    (tmp_path / ".trash" / "old" / "f").write_bytes(b"z" * 7)

    assert storage.export("a").name == "same-title.mp4" and storage.export("b").name == "same-title-2.mp4"
    u = storage.usage()
    assert (u["videos"], u["cache"], u["trash"]) == (20, 100, 7)  # b is still generating: its cache is not offered
    assert storage.clear_cache() == 100 and (tmp_path / "b" / "work" / "public" / "rife").exists()
    assert storage.empty_trash() == 7 and not (tmp_path / ".trash").exists()
