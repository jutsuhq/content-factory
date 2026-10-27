import subprocess

from factory.music import library
from factory.voice.audio import duration, has_audio, mix_music

TRACKS = [
    {"id": "calm", "file": "calm.m4a", "moods": ["calm", "ambient"], "default": True},
    {"id": "epic", "file": "epic.m4a", "moods": ["epic", "drums", "tense"]},
]


def test_pick_by_id_by_mood_or_none(monkeypatch):
    monkeypatch.setattr(library, "tracks", lambda: TRACKS)
    assert library.pick("epic")["id"] == "epic"
    assert library.pick("none") is None
    assert library.pick("tense drums")["id"] == "epic"
    assert library.pick(None, "что если")["id"] == "calm"  # nothing matches: the default track


def test_music_bed_is_looped_to_the_video_length(tmp_path):
    video, music, out = tmp_path / "v.mp4", tmp_path / "m.wav", tmp_path / "o.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=black:s=64x64:d=4",
            "-f",
            "lavfi",
            "-i",
            "sine=f=220:d=4",
            "-shortest",
            str(video),
        ],
        check=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=f=440:d=1.5", str(music)], check=True
    )
    mix_music(video, music, out, 4.0)
    assert has_audio(out) and abs(duration(out) - 4.0) < 0.1
