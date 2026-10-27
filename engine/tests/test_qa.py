from factory.stages.qa import file_checks, music_checks, text_checks, voice_checks


def words(*spans):
    return [{"word": f"w{k}", "start": a, "end": b} for k, (a, b) in enumerate(spans)]


def timeline(**beat):
    return {
        "hook": "Что если Луна исчезнет?",
        "beats": [
            {
                "counter": "НОЧЬ 1",
                "caption": "Луна пропала",
                "voice": "voice/01.wav",
                "words": words((0, 0.4), (0.5, 0.9)),
                **beat,
            }
        ],
    }


LIMITS = {"counter": 12, "caption": 60, "hook": 60, "subtitle": 44}


def ids(checks):
    return [c["id"] for c in checks]


def test_text_that_overflows_the_frame_is_flagged():
    tl = timeline(counter="ДВЕ ТЫСЯЧИ ЛЕТ", caption="x" * 70)
    assert ids(text_checks(tl, LIMITS)) == ["counter-long", "caption-long"]
    assert text_checks(timeline(), LIMITS) == []


def test_a_long_silence_is_a_gap_unless_the_script_asks_for_a_pause():
    tl = timeline(words=words((0, 0.4), (2.8, 3.2)))
    assert ids(voice_checks(tl, ["раз два"], [1.0], [1.0])) == ["voice-gap"]
    assert voice_checks(tl, ["раз [pause 1.0] два"], [1.0], [1.0]) == []
    assert ids(voice_checks(tl, ["раз [pause] два"], [1.0], [1.0])) == ["voice-gap"]  # 2.4s is over 0.5 + 1.8


def test_rushed_unclear_and_unaligned_voice():
    assert ids(voice_checks(timeline(), ["раз два"], [1.2], [0.5])) == ["voice-rushed", "voice-unclear"]
    assert ids(voice_checks(timeline(words=[]), ["раз два"], [1.0], [None])) == ["words-missing"]
    assert ids(voice_checks(timeline(voice=None), ["раз два"], [None], [None])) == ["voice-missing"]
    assert voice_checks(timeline(voice=None), [""], [None], [None]) == []


def test_file_checks():
    good = {"seconds": 31.0, "has_audio": True, "black": [], "loudness": -14.2, "peak": -1.6}
    assert file_checks(good, 31.0) == []
    bad = {"seconds": 28.0, "has_audio": True, "black": [(3.0, 3.6)], "loudness": -20.0, "peak": -0.2}
    assert ids(file_checks(bad, 31.0)) == ["length", "black", "loudness", "peak"]
    assert ids(file_checks({**good, "has_audio": False}, 31.0)) == ["no-audio"]


def test_music_needs_a_licence():
    assert music_checks(None)[0]["level"] == "info"
    assert music_checks({"title": "x", "author": "y"})[0]["id"] == "music-license"
    assert (
        music_checks({"title": "x", "author": "y", "license": "CC0", "source": "https://opengameart.org"})[0]["level"]
        == "info"
    )
