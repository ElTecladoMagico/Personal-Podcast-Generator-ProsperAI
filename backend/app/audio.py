"""MP3 assembly with ffmpeg (ADR 0016): join the TTS chunks, change tempo, measure durations."""

import subprocess
from pathlib import Path

LOUDNESS_LUFS = -16  # podcast standard


def assemble(parts: list[Path], gaps: list[float], out: Path, speed: float) -> None:
    """One ffmpeg pass: a pause after each chunk, all joined, the whole episode brought to
    podcast loudness and sped up by `speed`, encoded once. Chunks are not evened out one by one:
    each mixes both hosts, so that would shift the quieter host's level every chapter."""
    inputs, chains = [], []
    for i, (part, gap) in enumerate(zip(parts, gaps, strict=True)):
        inputs += ["-i", str(part)]
        pad = f",apad=pad_dur={gap}" if gap > 0 else ""  # apad with no length pads forever
        chains.append(f"[{i}:a]aresample=44100,aformat=channel_layouts=mono{pad}[a{i}]")
    joined = "".join(f"[a{i}]" for i in range(len(parts)))
    graph = ";".join(chains) + (
        f";{joined}concat=n={len(parts)}:v=0:a=1,"
        f"loudnorm=I={LOUDNESS_LUFS}:TP=-1.5:LRA=11,aresample=44100,atempo={speed}[out]"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph,
         "-map", "[out]", "-c:a", "libmp3lame", "-b:a", "128k", str(out)],
        check=True,
    )  # fmt: skip


def change_tempo(src: Path, out: Path, factor: float) -> None:
    """Speed speech up (factor > 1) without changing the pitch of the voices."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-filter:a",
            f"atempo={factor}",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            str(out),
        ],
        check=True,
    )


def duration(path: Path) -> float:
    """Seconds of audio, as decoded by ffprobe (not the header's estimate)."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())
