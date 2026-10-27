from factory.stages.align import match


def heard(*items):
    return [{"word": w, "start": s, "end": e} for w, s, e in items]


def test_exact_words_take_whisper_times():
    out = match(["Сегодня", "ночью"], heard((" Сегодня", 0.0, 0.9), (" ночью", 0.9, 1.3)))
    assert [(w["word"], w["start"], w["end"]) for w in out] == [("Сегодня", 0.0, 0.9), ("ночью", 0.9, 1.3)]


def test_misheard_stretch_is_spread_over_script_words():
    # Whisper heard "нет" where the script says "не от"
    out = match(
        ["разве", "не", "от", "комаров?"], heard(("разве", 1.0, 1.4), ("нет", 1.4, 1.8), ("комаров?", 1.8, 2.3))
    )
    assert [w["word"] for w in out] == ["разве", "не", "от", "комаров?"]
    assert out[1]["start"] == 1.4 and out[2]["end"] == 1.8


def test_invented_tail_is_dropped_and_missing_words_get_neighbour_times():
    out = match(["тишина.", "Стоп,"], heard(("тишина.", 5.0, 5.5), ("Продолжение", 5.6, 6.0), ("следует...", 6.0, 6.5)))
    assert len(out) == 2
    assert out[0]["start"] == 5.0
    assert out[1]["start"] >= out[0]["end"]
