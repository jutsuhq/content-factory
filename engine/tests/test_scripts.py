import json

import pytest

from factory.core import formats
from factory.studio import compose, store, translate


def test_blank_script_is_valid_but_not_ready():
    b = compose.blank("What if the Moon disappeared", 60, "toon-homestead", None, True, "en")
    assert len(b["beats"]) == 10 and all(beat["vo"] == "" for beat in b["beats"])
    assert not [p for p in compose.problems(b) if p.startswith("schema")]
    assert compose.missing(b)[:2] == ["hook", "camera"] and "beat 8 vo" in compose.missing(b)
    assert "vo" not in compose.blank("x", 30, "toon-homestead", None, False, "en")["beats"][0]


def test_pause_marks_are_not_digits_in_the_voice():
    b = compose.blank("x", 30, "toon-homestead", None, True, "en")
    b["beats"][0]["vo"] = "Ten thousand years later. [pause 0.4] It started today."
    assert not [p for p in compose.problems(b) if "digits" in p]
    b["beats"][0]["vo"] = "Year 300."
    assert "beat 1: vo has digits, write numbers as words" in compose.problems(b)


def test_guide_carries_rules_fields_and_an_example():
    g = compose.guide("de")
    assert "German" in g and "camera: English" in g and '"beats"' in g


@pytest.fixture
def episodes(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "EPISODES", tmp_path)
    monkeypatch.setattr(translate, "EPISODES", tmp_path)
    beats = json.loads(formats.examples(formats.load())[0].read_text(encoding="utf-8"))
    (tmp_path / "moon").mkdir()
    (tmp_path / "moon" / "beats.json").write_text(json.dumps(beats), encoding="utf-8")
    frames = tmp_path / "moon" / "work" / "public" / "frames"
    frames.mkdir(parents=True)
    (frames / "01-916.png").write_bytes(b"png")
    return tmp_path, beats


def test_copy_in_another_language_takes_given_texts_and_shares_frames(episodes):
    root, beats = episodes
    lines = [{"counter": f"DAY {i}", "caption": "c", "vo": "v"} for i in range(len(beats["beats"]))]
    slug = translate.translate("moon", "de", {"hook": "Was wäre, wenn", "beats": lines})
    new = json.loads((root / slug / "beats.json").read_text(encoding="utf-8"))
    assert new["language"] == "de" and new["hook"] == "Was wäre, wenn" and new["beats"][1]["counter"] == "DAY 1"
    assert new["beats"][1]["state"] == beats["beats"][1]["state"]  # the picture is untouched
    assert (root / slug / "work" / "public" / "frames" / "01-916.png").stat().st_ino == (
        root / "moon" / "work" / "public" / "frames" / "01-916.png"
    ).stat().st_ino
    with pytest.raises(ValueError):
        translate.translate("moon", "de", {"beats": lines[:2]})


def test_copy_without_texts_keeps_the_original_for_hand_editing(episodes):
    root, beats = episodes
    new = json.loads((root / translate.translate("moon", "es") / "beats.json").read_text(encoding="utf-8"))
    assert new["hook"] == beats["hook"] and new["language"] == "es"


def test_blank_drawn_waits_for_svg():
    b = compose.blank("x", 30, "gouache", None, False, "en", "drawn")
    assert b["render_mode"] == "drawn" and "camera" not in b
    assert "svg" in b["beats"][0] and "state" not in b["beats"][0]
    assert not any(i.startswith("schema") for i in compose.problems(b))
    assert "beat 1 svg" in compose.missing(b)
