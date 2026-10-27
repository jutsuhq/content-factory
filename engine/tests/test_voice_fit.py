from factory.voice.fit import PACE, TAIL, beat_length, tempo


def test_a_line_that_fits_runs_at_the_base_pace():
    assert tempo(5.0, 7.0) == PACE


def test_a_long_line_speeds_up_just_enough():
    assert tempo(7.6, 7.0) == round(7.6 / (7.0 - TAIL), 3)


def test_speed_up_is_capped():
    assert tempo(10.0, 7.0) == 1.2


def test_a_voiced_beat_lasts_as_long_as_its_line():
    assert beat_length(9.0, 5.0) == 5.0 + TAIL  # no picture held in silence
    assert beat_length(7.0, 10.0 / 1.2) == 10.0 / 1.2 + TAIL
    assert beat_length(6.0, 0.8) == 2.0


def test_beat_without_voice_keeps_its_seconds():
    assert beat_length(6.0, None) == 6.0
