"""MP3 assembly with ffmpeg (ADR 0016): concatenate the TTS chunks and measure durations."""

import subprocess
import tempfile
from pathlib import Path


def concat_mp3(parts: list[Path], out: Path) -> None:
    """Join MP3 chunks without re-encoding. ffmpeg (unlike a raw byte concat) rewrites the
    Xing header, so players show the real total duration."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt") as listing:
        listing.writelines(f"file '{Path(p).resolve()}'\n" for p in parts)
        listing.flush()
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                listing.name,
                "-c",
                "copy",
                str(out),
            ],
            check=True,
        )


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
