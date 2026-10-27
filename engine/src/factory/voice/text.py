"""Script lines before TTS.

Markup a `vo` line may carry:
  [pause] or [pause 0.8]  silence of 0.5 s (or the given seconds) at that point
  w+ord                    engine markup, e.g. a stress for a voice that reads `+`; hidden in subtitles

Numbers should already be words (the script writer is told so, and only it can inflect them for the sentence).
Digits that slip through are read out by num2words in the nominative, which beats a failed render.
"""

from __future__ import annotations

import re

PAUSE = re.compile(r"\[pause(?:\s+(\d+(?:[.,]\d+)?)\s*s?)?\]", re.I)
DEFAULT_PAUSE = 0.5
MAX_PAUSE = 3.0

_INVISIBLE = re.compile("[\u200b-\u200f\u2060\ufeff]")
_REPEATS = re.compile(r"([!?.,…-])\1{3,}")  # "!!!!!!" makes some engines hum or stall
_NUMBER = re.compile(r"(?<![\w.,-])(\d{1,9})(?:[.,](\d{1,3}))?(?![\w])")


def clean(text: str) -> str:
    text = _INVISIBLE.sub("", text)
    text = _REPEATS.sub(r"\1\1\1", text)
    return re.sub(r"\s+", " ", text).strip()


def numbers_to_words(text: str, language: str) -> str:
    from num2words import num2words

    def say(m: re.Match) -> str:
        value = float(f"{m.group(1)}.{m.group(2)}") if m.group(2) else int(m.group(1))
        try:
            return num2words(value, lang=language)
        except NotImplementedError:
            return m.group(0)

    return _NUMBER.sub(say, text)


def chunks(line: str) -> list[tuple[str, float]]:
    """Split a line at pause marks: [(text, pause after it in seconds), ...]."""
    out, start = [], 0
    for m in PAUSE.finditer(line):
        seconds = float(m.group(1).replace(",", ".")) if m.group(1) else DEFAULT_PAUSE
        out.append((line[start : m.start()].strip(), min(seconds, MAX_PAUSE)))
        start = m.end()
    out.append((line[start:].strip(), 0.0))
    # a pause at the very start or two marks in a row leave empty text: fold their silence into the previous chunk
    merged: list[tuple[str, float]] = []
    for text, pause in out:
        if not text and merged:
            merged[-1] = (merged[-1][0], merged[-1][1] + pause)
        elif text or not merged:
            merged.append((text, pause))
    return [(t, p) for t, p in merged if t]


def prepare(line: str, language: str) -> str:
    """The line as it will be spoken: cleaned, numbers in words, markup kept for `chunks`."""
    line, out, start = clean(line), [], 0
    for m in PAUSE.finditer(line):  # the seconds inside a pause mark stay digits
        out += [numbers_to_words(line[start : m.start()], language), m.group(0)]
        start = m.end()
    return "".join(out + [numbers_to_words(line[start:], language)])


def display(line: str) -> str:
    """The line as it is shown in subtitles: no pause marks, no `+` marks."""
    return re.sub(r"\s+", " ", PAUSE.sub(" ", line).replace("+", "")).strip()
