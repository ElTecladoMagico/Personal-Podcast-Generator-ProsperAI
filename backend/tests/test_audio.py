import subprocess

import pytest

from app.audio import concat_mp3, duration


def tone(path, seconds: float, freq: int) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={freq}:duration={seconds}",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            "-ar",
            "44100",
            str(path),
        ],
        check=True,
    )


def test_concat_keeps_the_real_total_duration(tmp_path):
    a, b, out = tmp_path / "a.mp3", tmp_path / "b.mp3", tmp_path / "out.mp3"
    tone(a, 1, 440)
    tone(b, 1.5, 660)
    concat_mp3([a, b], out)
    assert duration(a) == pytest.approx(1.0, abs=0.06)
    assert duration(out) == pytest.approx(2.5, abs=0.1)


def test_duration_of_a_missing_file_fails(tmp_path):
    with pytest.raises(subprocess.CalledProcessError):
        duration(tmp_path / "nope.mp3")
