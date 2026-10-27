"""tts: one voice track per beat from its `vo` line.

Per beat: the line is cleaned and split at [pause] marks (voice.text); each piece is spoken by the episode
language's voice (providers.tts); the pieces are trimmed and joined with their silences into NN.raw.wav. Then NN.wav
is NN.raw.wav sped up just enough to fit the beat (voice.fit). The two files are cached apart, so changing a beat's
seconds does not re-synthesise it.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from factory.core import Episode, digest, fresh, mark, voice_for
from factory.providers import tts as engines
from factory.voice import audio, fit, text


def synthesize(line: str, voice: dict, out: Path) -> None:
    """Speak one prepared line, markup included, into a trimmed wav."""
    say = engines.speaker(voice)
    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for k, (piece, pause) in enumerate(text.chunks(line)):
            spoken, wav = Path(tmp) / f"{k:02d}.raw.wav", Path(tmp) / f"{k:02d}.wav"
            say(piece, spoken)
            audio.trim(spoken, wav)  # engines pad each piece with silence: cut it, or a pause comes out twice as long
            parts.append((wav, pause))
        audio.join(parts, out)


def run(ep: Episode, profile: dict) -> None:
    voice = voice_for(profile, ep.language)
    if ep.language not in engines.engine(voice).LANGUAGES:
        raise SystemExit(f"tts engine {voice['engine']} does not speak {ep.language}")
    d = ep.work("voice")
    made = 0
    for i, beat in enumerate(ep.beats["beats"], 1):
        line = text.prepare(beat.get("vo", ""), ep.language)
        if not line:
            continue
        raw, out = d / f"{i:02d}.raw.wav", d / f"{i:02d}.wav"
        raw_key = digest(line, voice)
        if not fresh(raw, raw_key):
            synthesize(line, voice, raw)
            mark(raw, raw_key)
            made += 1
        factor = fit.tempo(audio.duration(raw), beat["seconds"])
        key = digest(raw, factor)
        if not fresh(out, key):
            audio.speed(raw, out, factor)
            mark(out, key)
            print(f"tts: {out.name} {audio.duration(out):.1f}s" + (f" (x{factor})" if factor > 1 else ""), flush=True)
    print(f"tts: {made} synthesised")
