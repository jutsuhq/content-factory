import math
import struct
import wave

from factory.voice.audio import duration, join, speed, trim

RATE = 22050


def tone(path, seconds, lead=0.0, tail=0.0):
    frames = [0] * int(lead * RATE) + [
        int(8000 * math.sin(2 * math.pi * 220 * i / RATE)) for i in range(int(seconds * RATE))
    ]
    frames += [0] * int(tail * RATE)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(struct.pack(f"<{len(frames)}h", *frames))
    return path


def test_join_puts_the_pause_between_pieces(tmp_path):
    a, b = tone(tmp_path / "a.wav", 1.0), tone(tmp_path / "b.wav", 0.5)
    join([(a, 0.4), (b, 0.0)], tmp_path / "j.wav")
    assert abs(duration(tmp_path / "j.wav") - 1.9) < 0.01


def test_trim_cuts_silence_at_both_edges(tmp_path):
    src = tone(tmp_path / "s.wav", 1.0, lead=0.6, tail=0.8)
    trim(src, tmp_path / "t.wav")
    assert abs(duration(tmp_path / "t.wav") - 1.0) < 0.1


def test_speed_keeps_length_proportional(tmp_path):
    src = tone(tmp_path / "s.wav", 2.4)
    speed(src, tmp_path / "f.wav", 1.2)
    assert abs(duration(tmp_path / "f.wav") - 2.0) < 0.05
