import subprocess

import pytest

from app.audio import duration


def tone(path, seconds: float, freq: int, volume: float = 1.0) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={freq}:duration={seconds}",
            "-af",
            f"volume={volume}",
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


def test_duration_of_a_missing_file_fails(tmp_path):
    with pytest.raises(subprocess.CalledProcessError):
        duration(tmp_path / "nope.mp3")


def test_change_tempo_shortens_by_the_factor(tmp_path):
    from app.audio import change_tempo

    src, out = tmp_path / "a.mp3", tmp_path / "fast.mp3"
    tone(src, 2.2, 440)
    change_tempo(src, out, 1.1)
    assert duration(out) == pytest.approx(2.0, abs=0.08)


def mean_volume(path, start: float, seconds: float) -> float:
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-ss", str(start), "-t", str(seconds), "-i", str(path),
         "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    ).stderr  # fmt: skip
    return float(out.split("mean_volume:")[1].split("dB")[0])


def test_assemble_adds_pauses_evens_out_loudness_and_speeds_up(tmp_path):
    from app.audio import assemble

    loud, quiet, out = tmp_path / "loud.mp3", tmp_path / "quiet.mp3", tmp_path / "out.mp3"
    tone(loud, 3, 440, volume=0.9)
    tone(quiet, 3, 440, volume=0.15)  # ~15 dB quieter, like a host rendered softer by one request
    assemble([loud, quiet], [1.0, 0.0], out, speed=1.1)

    assert duration(out) == pytest.approx((3 + 1 + 3) / 1.1, abs=0.15)
    first, second = mean_volume(out, 0.3, 2), mean_volume(out, 4.0 / 1.1 + 0.3, 2)
    assert abs(first - second) < 1.5  # same loudness after the join
    assert mean_volume(out, 3.1 / 1.1, 0.6) < -60  # the pause is silence
