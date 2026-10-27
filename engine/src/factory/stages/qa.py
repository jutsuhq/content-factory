"""qa: check the finished video before anyone posts it. Measures the file (length, black frames, loudness, an audio
stream) and reads the timeline for what a viewer would notice: rushed or silent voice, long gaps, text that will not
fit the screen, music without a licence. Writes out/qa.json; never fails the job, the review page shows the list."""

from __future__ import annotations

import itertools
import json
import re
import shutil
import subprocess
from pathlib import Path

from factory.core import Episode
from factory.voice import audio, fit, text

LOUDNESS, LOUDNESS_SLACK, MAX_PEAK = -14.0, 1.5, -1.0
MAX_GAP = 1.8  # silence between two words that reads as a glitch, on top of written pauses
MIN_HEARD = 0.7  # share of script words the recogniser heard back; less usually means a garbled voice


def _check(level: str, cid: str, message: str, beat: int | None = None) -> dict:
    return {"level": level, "id": cid, "message": message, **({"beat": beat} if beat else {})}


def text_checks(tl: dict, limits: dict[str, int]) -> list[dict]:
    """limits: the format's `text_limits`, characters per timeline text (top-level or per beat) before it overflows
    the frame; `subtitle` caps four spoken words shown together."""
    out = []
    for field, cap in limits.items():
        if isinstance(tl.get(field), str) and len(tl[field]) > cap:
            out.append(_check("warn", f"{field}-long", f"{field} is {len(tl[field])} characters, max {cap}"))
    for i, b in enumerate(tl["beats"], 1):
        for field, cap in limits.items():
            if isinstance(b.get(field), str) and len(b[field]) > cap:
                out.append(
                    _check("warn", f"{field}-long", f"{field} “{b[field]}” is {len(b[field])} characters, max {cap}", i)
                )
        words = [w["word"] for w in b.get("words") or []]
        for k in range(0, len(words), 4):
            chunk = " ".join(words[k : k + 4])
            if "subtitle" in limits and len(chunk) > limits["subtitle"]:
                out.append(
                    _check(
                        "warn",
                        "subtitle-long",
                        f"subtitle “{chunk}” is {len(chunk)} characters, it may cover the picture",
                        i,
                    )
                )
    return out


def voice_checks(tl: dict, lines: list[str], tempos: list[float | None], heard: list[float | None]) -> list[dict]:
    """lines: the written vo per beat; tempos: speed-up applied per beat; heard: share of words the recogniser got."""
    out = []
    for i, (b, line, factor, ratio) in enumerate(zip(tl["beats"], lines, tempos, heard, strict=False), 1):
        if not line.strip():
            continue
        if not b.get("voice"):
            out.append(_check("error", "voice-missing", "the beat has a line but no voice", i))
            continue
        if not b["words"]:
            out.append(_check("error", "words-missing", "no subtitles: the voice was not aligned", i))
            continue
        if factor and factor >= fit.MAX_TEMPO - 0.005:
            out.append(
                _check(
                    "warn",
                    "voice-rushed",
                    f"voice sped up ×{factor:.2f} (the cap) and still runs long: shorten the line",
                    i,
                )
            )
        if ratio is not None and ratio < MIN_HEARD:
            out.append(
                _check(
                    "warn",
                    "voice-unclear",
                    f"the recogniser heard only {ratio:.0%} of the words: listen for mispronunciations",
                    i,
                )
            )
        allowed = MAX_GAP + max(pause for _, pause in text.chunks(line))
        for a, z in itertools.pairwise(b["words"]):
            if z["start"] - a["end"] > allowed:
                out.append(
                    _check("warn", "voice-gap", f"{z['start'] - a['end']:.1f}s of silence after “{a['word']}”", i)
                )
    return out


def measure(video: Path) -> dict:
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    r = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostats",
            "-i",
            str(video),
            "-vf",
            "blackdetect=d=0.4:pix_th=0.08",
            "-af",
            "ebur128=peak=true",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    summary = r.stderr.rsplit("Summary:", 1)[-1]
    num = lambda pat: float(m.group(1)) if (m := re.search(pat, summary)) else None  # noqa: E731
    black = [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)]
    return {
        "seconds": audio.duration(video),
        "has_audio": audio.has_audio(video),
        "black": black,
        "loudness": num(r"I:\s+(-?[\d.]+) LUFS"),
        "peak": num(r"Peak:\s+(-?[\d.]+) dBFS"),
    }


def file_checks(m: dict, expected: float) -> list[dict]:
    out = []
    if abs(m["seconds"] - expected) > 0.25:
        out.append(_check("error", "length", f"video is {m['seconds']:.1f}s, the timeline says {expected:.1f}s"))
    for a, z in m["black"]:
        out.append(_check("error", "black", f"black frames {a:.1f}–{z:.1f}s"))
    if not m["has_audio"]:
        out.append(_check("error", "no-audio", "the video has no sound"))
    elif m["loudness"] is not None and abs(m["loudness"] - LOUDNESS) > LOUDNESS_SLACK:
        out.append(_check("warn", "loudness", f"loudness {m['loudness']:.1f} LUFS, apps expect {LOUDNESS:.0f}"))
    if m["peak"] is not None and m["peak"] > MAX_PEAK:
        out.append(_check("warn", "peak", f"peak {m['peak']:.1f} dBFS, may clip after the app re-encodes it"))
    return out


def music_checks(track: dict | None) -> list[dict]:
    if not track:
        return [_check("info", "music-none", "no music")]
    if not track.get("license") or not track.get("source"):
        return [_check("error", "music-license", f"music “{track.get('title')}” has no recorded licence")]
    return [_check("info", "music", f"music: {track['title']} by {track['author']} ({track['license']})")]


def run(ep: Episode, profile: dict) -> None:
    out_dir = ep.dir / "out"
    video = out_dir / f"{ep.slug}.mp4"
    tl = json.loads((ep.work() / "timeline.json").read_text(encoding="utf-8"))["timeline"]
    voice = ep.work("voice")
    lines, tempos, heard = [], [], []
    for i, beat in enumerate(ep.beats["beats"], 1):
        lines.append(beat.get("vo", "") if ep.beats.get("voice") else "")
        raw, final = voice / f"{i:02d}.raw.wav", voice / f"{i:02d}.wav"
        tempos.append(audio.duration(raw) / audio.duration(final) if raw.exists() and final.exists() else None)
        match = voice / f"{i:02d}.match.json"
        heard.append(json.loads(match.read_text())["heard"] if match.exists() else None)
    music = out_dir / "music.json"
    checks = (
        file_checks(measure(video), tl["duration"])
        + voice_checks(tl, lines, tempos, heard)
        + text_checks(tl, ep.format.get("text_limits") or {})
        + music_checks(json.loads(music.read_text(encoding="utf-8")) if music.exists() else None)
    )
    errors = sum(c["level"] == "error" for c in checks)
    warns = sum(c["level"] == "warn" for c in checks)
    (out_dir / "qa.json").write_text(
        json.dumps({"ok": errors == 0, "checks": checks}, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"qa: {'ok' if not errors else f'{errors} error(s)'}, {warns} warning(s)")
