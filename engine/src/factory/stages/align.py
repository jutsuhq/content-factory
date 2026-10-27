"""align: word timings for subtitles. The words come from the script, only the timings from Whisper.

Whisper mishears and invents tails ("Продолжение следует..."), so script words are matched to recognised
words, and a script word with no match takes its time from its neighbours.
"""

from __future__ import annotations

import difflib
import json
import re

from factory.core import Episode, digest, fresh, mark
from factory.providers import stt
from factory.voice import text


def _norm(word: str) -> str:
    return re.sub(r"[^\w]", "", word.lower().replace("ё", "е"))


def match(script: list[str], heard: list[dict]) -> list[dict]:
    """Give each script word a start and end from the recognised words."""
    sm = difflib.SequenceMatcher(a=[_norm(w) for w in script], b=[_norm(h["word"]) for h in heard], autojunk=False)
    times: list[tuple[float, float] | None] = [None] * len(script)
    for tag, a0, a1, b0, b1 in sm.get_opcodes():
        if tag == "equal":
            for k in range(a1 - a0):
                times[a0 + k] = (heard[b0 + k]["start"], heard[b0 + k]["end"])
        elif tag == "replace" and b1 > b0:
            # spread the misheard stretch evenly over the script words it stands for
            start, end = heard[b0]["start"], heard[b1 - 1]["end"]
            step = (end - start) / (a1 - a0)
            for k in range(a1 - a0):
                times[a0 + k] = (start + k * step, start + (k + 1) * step)
    filled: list[tuple[float, float]] = []
    for i, t in enumerate(times):
        if t is None:
            prev = filled[-1][1] if filled else 0.0
            nxt = next((u[0] for u in times[i + 1 :] if u), prev + 0.3)
            filled.append((prev, max(prev, nxt)))
        else:
            filled.append(t)
    return [{"word": w, "start": round(s, 3), "end": round(e, 3)} for w, (s, e) in zip(script, filled, strict=True)]


def heard_share(script: list[str], heard: list[dict]) -> float:
    """How much of the script the recogniser heard word for word: a garbled or skipped word lowers it."""
    sm = difflib.SequenceMatcher(a=[_norm(w) for w in script], b=[_norm(h["word"]) for h in heard], autojunk=False)
    return round(sum(b.size for b in sm.get_matching_blocks()) / max(1, len(script)), 3)


def run(ep: Episode, profile: dict) -> None:
    d = ep.work("voice")
    made = 0
    for i, beat in enumerate(ep.beats["beats"], 1):
        wav, out = d / f"{i:02d}.wav", d / f"{i:02d}.words.json"
        if not wav.exists():
            continue
        script = text.display(text.prepare(beat.get("vo", ""), ep.language)).split()
        key = digest(wav, script)
        if fresh(out, key) and (d / f"{i:02d}.match.json").exists():
            continue
        heard = stt.words(profile["providers"]["stt"], wav, ep.language, profile["stt_model"])
        out.write_text(json.dumps(match(script, heard), ensure_ascii=False, indent=1), encoding="utf-8")
        (d / f"{i:02d}.match.json").write_text(json.dumps({"heard": heard_share(script, heard)}), encoding="utf-8")
        mark(out, key)
        made += 1
    print(f"align: {made} made")
