"""How fast a beat's voice may run. Short videos live on pace: a line longer than its beat is first sped up a little
(pitch kept), and the beat on screen follows its voice, so no picture is held in silence."""

from __future__ import annotations

PACE = 1.1  # every line runs this much faster than the engine speaks: TTS narration is slower than short-video voices
MAX_TEMPO = 1.2  # faster than this starts to sound rushed
TAIL = 0.45  # pause after the last word of a beat before the next beat's voice
MIN_BEAT = 2.0  # the shortest beat on screen, so a morph and a counter still read


def tempo(voice_seconds: float, beat_seconds: float, max_tempo: float = MAX_TEMPO, tail: float = TAIL) -> float:
    """PACE when the line fits the beat, otherwise just fast enough to fit, capped at max_tempo."""
    budget = beat_seconds - tail
    if budget <= 0 or voice_seconds / PACE <= budget:
        return PACE
    return round(min(max_tempo, voice_seconds / budget), 3)


def beat_length(beat_seconds: float, voice_seconds: float | None, tail: float = TAIL) -> float:
    """The beat on screen. A voiced beat lasts as long as its (sped up) line plus a breath, whatever its seconds say:
    holding a picture after the line ends is what makes a video feel slow. A silent beat keeps its seconds."""
    return beat_seconds if voice_seconds is None else max(MIN_BEAT, voice_seconds + tail)
