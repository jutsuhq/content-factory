from factory.voice.text import chunks, clean, display, numbers_to_words, prepare


def test_pause_marks_split_the_line_and_carry_their_length():
    assert chunks("Silence. [pause] And then [pause 1.2] a bang.") == [
        ("Silence.", 0.5),
        ("And then", 1.2),
        ("a bang.", 0.0),
    ]


def test_pause_mark_comma_decimal_and_cap():
    assert chunks("One [PAUSE 0,8] two [pause 9]") == [("One", 0.8), ("two", 3.0)]


def test_marks_in_a_row_add_up_and_a_leading_mark_is_dropped():
    assert chunks("[pause] One [pause] [pause 0.3] two") == [("One", 0.8), ("two", 0.0)]


def test_display_drops_markup_but_keeps_words():
    assert display("The old c+astle [pause] creaks.") == "The old castle creaks."


def test_digits_become_words_in_the_episode_language():
    assert numbers_to_words("in 3 days", "en") == "in three days"
    assert numbers_to_words("en 3 días", "es") == "en tres días"


def test_codes_and_words_with_digits_are_left_alone():
    assert numbers_to_words("Covid-19 and v2", "en") == "Covid-19 and v2"


def test_clean_drops_invisible_chars_and_caps_repeats():
    assert clean("Stop!!!!!!\u200b  now") == "Stop!!! now"


def test_pause_seconds_stay_digits():
    assert prepare("One [pause 0.8] 2", "en") == "One [pause 0.8] two"


def test_prepare_is_idempotent():
    once = prepare("In 5 years [pause] all gone!!!!", "en")
    assert prepare(once, "en") == once
