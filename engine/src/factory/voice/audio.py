"""ffmpeg and wave work on voice tracks and the final video. Every function writes a new file and leaves its input."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import wave
from pathlib import Path

LOUDNESS = -14.0  # LUFS, what TikTok, Reels and Shorts play at
TRUE_PEAK = -1.5
SILENCE_DB = -45


def _ffmpeg(*args: str) -> subprocess.CompletedProcess:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise SystemExit("ffmpeg not found: run `factory doctor`")
    return subprocess.run([exe, "-hide_banner", "-y", *args], capture_output=True, text=True, check=True)


def duration(path: Path) -> float:
    """Seconds of a WAV (read directly) or of any media file (ffprobe)."""
    if Path(path).suffix == ".wav":
        with wave.open(str(path)) as w:
            return w.getnframes() / w.getframerate()
    probe = subprocess.run(
        [
            shutil.which("ffprobe") or "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(probe.stdout.strip())


def join(parts: list[tuple[Path, float]], out: Path) -> None:
    """Concatenate wavs of one engine, each followed by its seconds of silence."""
    with wave.open(str(parts[0][0])) as first:
        params = first.getparams()
    with wave.open(str(out), "wb") as dst:
        dst.setparams(params)
        for wav, pause in parts:
            with wave.open(str(wav)) as src:
                dst.writeframes(src.readframes(src.getnframes()))
            dst.writeframes(b"\0" * int(pause * params.framerate) * params.sampwidth * params.nchannels)


def trim(src: Path, out: Path) -> None:
    """Cut leading and trailing silence the engine leaves, so beats start on the word."""
    edge = f"silenceremove=start_periods=1:start_threshold={SILENCE_DB}dB:start_silence=0.05"
    _ffmpeg("-i", str(src), "-af", f"{edge},areverse,{edge},areverse", str(out))


def speed(src: Path, out: Path, factor: float) -> None:
    """Faster or slower with the pitch kept (atempo)."""
    if abs(factor - 1) < 1e-3:
        shutil.copyfile(src, out)
        return
    _ffmpeg("-i", str(src), "-af", f"atempo={factor}", str(out))


def loudness(src: Path, out: Path, target: float = LOUDNESS) -> dict:
    """Two-pass EBU R128 normalisation of a video's audio; the video stream is copied untouched."""
    spec = f"loudnorm=I={target}:TP={TRUE_PEAK}:LRA=11"
    probe = _ffmpeg("-i", str(src), "-af", f"{spec}:print_format=json", "-vn", "-f", "null", "-")
    m = json.loads(re.findall(r"\{[^{}]+\}", probe.stderr)[-1])
    applied = (
        f"{spec}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
        f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true"
    )
    _ffmpeg("-i", str(src), "-af", applied, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(out))
    return {"before": float(m["input_i"]), "after": target}


MUSIC_UNDER_VOICE = -9.0  # dB on a track levelled to -20 LUFS: a bed under the voice, not a second voice
MUSIC_ALONE = -2.0  # dB when the video has no voice


def has_audio(video: Path) -> bool:
    probe = subprocess.run(
        [
            shutil.which("ffprobe") or "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=index",
            "-of",
            "csv=p=0",
            str(video),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(probe.stdout.strip())


def mix_music(video: Path, music: Path, out: Path, seconds: float) -> None:
    """Lay a looped music bed under the video's own audio. The bed fades in and out and ducks while someone speaks
    (sidechain compression keyed by the voice), so words stay on top without hand-drawn volume curves."""
    fade_out = max(0.0, seconds - 2.5)
    bed = (
        f"[1:a]atrim=0:{seconds:.3f},afade=t=in:d=1.2,afade=t=out:st={fade_out:.3f}:d=2.5,"
        f"aformat=sample_rates=48000:channel_layouts=stereo"
    )
    if has_audio(video):
        graph = (
            f"{bed},volume={MUSIC_UNDER_VOICE}dB[bed];"
            "[0:a]aformat=sample_rates=48000:channel_layouts=stereo,asplit=2[voice][key];"
            "[bed][key]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=450[ducked];"
            "[voice][ducked]amix=inputs=2:normalize=0:duration=first[a]"
        )
    else:
        graph = f"{bed},volume={MUSIC_ALONE}dB[a]"
    _ffmpeg(
        "-i",
        str(video),
        "-stream_loop",
        "-1",
        "-i",
        str(music),
        "-filter_complex",
        graph,
        "-map",
        "0:v",
        "-map",
        "[a]",
        "-t",
        f"{seconds:.3f}",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "320k",
        str(out),
    )
