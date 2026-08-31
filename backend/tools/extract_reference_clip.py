"""Deterministically select and normalize a clean 12-second reference clip."""

from __future__ import annotations

import argparse
import hashlib
import math
import os
import struct
import sys
import tempfile
import warnings
import wave
from dataclasses import dataclass
from pathlib import Path


with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    import audioop


WINDOW_SECONDS = 12.0
STEP_SECONDS = 0.25
TARGET_RATE = 24_000
TARGET_WIDTH = 2
TARGET_CHANNELS = 1
# The supplied recording's silent gaps are encoded as digital zero. A wider
# sample-amplitude threshold misclassifies ordinary zero crossings in quiet
# speech as silence, so allow only one quantization step around zero.
NEAR_SILENCE_THRESHOLD = 1
MAX_NEAR_SILENCE_RATIO = 0.20
CLIPPING_THRESHOLD = 32_767


@dataclass(frozen=True)
class WindowSelection:
    start_frame: int
    start_seconds: float
    rms: int
    near_silence_ratio: float
    pcm: bytes


@dataclass(frozen=True)
class ExtractionResult:
    input_path: Path
    output_path: Path
    start_seconds: float
    rms: int
    near_silence_ratio: float
    sample_rate: int
    channels: int
    sample_width: int
    frame_count: int
    duration_seconds: float
    sha256: str


def _samples(pcm: bytes) -> tuple[int, ...]:
    if len(pcm) % TARGET_WIDTH:
        raise ValueError("PCM16 data has an incomplete sample")
    if not pcm:
        return ()
    return struct.unpack(f"<{len(pcm) // TARGET_WIDTH}h", pcm)


def select_best_window(pcm: bytes, frame_rate: int) -> WindowSelection:
    """Choose the highest-RMS eligible window; ties keep the earliest start."""
    if frame_rate <= 0:
        raise ValueError("frame rate must be positive")

    window_frames = round(WINDOW_SECONDS * frame_rate)
    step_frames = round(STEP_SECONDS * frame_rate)
    if step_frames <= 0:
        raise ValueError("frame rate is too low for a 250 ms step")
    total_frames = len(pcm) // TARGET_WIDTH
    if total_frames < window_frames:
        raise ValueError("source audio is shorter than 12 seconds")

    best: WindowSelection | None = None
    window_bytes = window_frames * TARGET_WIDTH
    for start_frame in range(0, total_frames - window_frames + 1, step_frames):
        start_byte = start_frame * TARGET_WIDTH
        candidate = pcm[start_byte : start_byte + window_bytes]
        if audioop.max(candidate, TARGET_WIDTH) >= CLIPPING_THRESHOLD:
            continue

        candidate_samples = _samples(candidate)
        near_silence_count = sum(
            1 for sample in candidate_samples if abs(sample) <= NEAR_SILENCE_THRESHOLD
        )
        near_silence_ratio = near_silence_count / window_frames
        if near_silence_ratio > MAX_NEAR_SILENCE_RATIO:
            continue

        rms = audioop.rms(candidate, TARGET_WIDTH)
        if best is None or rms > best.rms:
            best = WindowSelection(
                start_frame=start_frame,
                start_seconds=start_frame / frame_rate,
                rms=rms,
                near_silence_ratio=near_silence_ratio,
                pcm=candidate,
            )

    if best is None:
        raise ValueError(
            "no eligible 12-second window (all windows clipped or exceeded 20% near-silence)"
        )
    return best


def select_manual_range(
    pcm: bytes,
    frame_rate: int,
    start_seconds: float,
    end_seconds: float,
) -> WindowSelection:
    """Select an approved complete-utterance range no longer than 12 seconds."""
    if frame_rate <= 0:
        raise ValueError("frame rate must be positive")
    if not math.isfinite(start_seconds) or not math.isfinite(end_seconds):
        raise ValueError("manual range boundaries must be finite")
    if start_seconds < 0 or end_seconds <= start_seconds:
        raise ValueError("manual range must have a non-negative start before its end")
    if end_seconds - start_seconds > WINDOW_SECONDS:
        raise ValueError("manual range must not exceed 12 seconds")

    total_frames = len(pcm) // TARGET_WIDTH
    start_frame = round(start_seconds * frame_rate)
    end_frame = round(end_seconds * frame_rate)
    if end_frame > total_frames:
        raise ValueError("manual range exceeds the source audio")

    candidate = pcm[start_frame * TARGET_WIDTH : end_frame * TARGET_WIDTH]
    if not candidate:
        raise ValueError("manual range contains no audio")
    if audioop.max(candidate, TARGET_WIDTH) >= CLIPPING_THRESHOLD:
        raise ValueError("manual range contains clipped samples")

    candidate_samples = _samples(candidate)
    near_silence_count = sum(
        1 for sample in candidate_samples if abs(sample) <= NEAR_SILENCE_THRESHOLD
    )
    near_silence_ratio = near_silence_count / len(candidate_samples)
    if near_silence_ratio > MAX_NEAR_SILENCE_RATIO:
        raise ValueError("manual range exceeded 20% near-silence")

    return WindowSelection(
        start_frame=start_frame,
        start_seconds=start_frame / frame_rate,
        rms=audioop.rms(candidate, TARGET_WIDTH),
        near_silence_ratio=near_silence_ratio,
        pcm=candidate,
    )


def _to_pcm16_mono(frames: bytes, sample_width: int, channels: int) -> bytes:
    if sample_width not in (1, 2, 3, 4):
        raise ValueError(f"unsupported WAV sample width: {sample_width}")
    if channels not in (1, 2):
        raise ValueError(f"unsupported WAV channel count: {channels}")

    converted = frames
    if sample_width == 1:
        # PCM WAV stores 8-bit samples unsigned; audioop operates on signed samples.
        converted = audioop.bias(converted, 1, -128)
    if sample_width != TARGET_WIDTH:
        converted = audioop.lin2lin(converted, sample_width, TARGET_WIDTH)
    if channels == 2:
        converted = audioop.tomono(converted, TARGET_WIDTH, 0.5, 0.5)
    return converted


def _resample_exact(pcm: bytes, source_rate: int) -> bytes:
    converted, _ = audioop.ratecv(
        pcm,
        TARGET_WIDTH,
        TARGET_CHANNELS,
        source_rate,
        TARGET_RATE,
        None,
    )
    required_bytes = round(WINDOW_SECONDS * TARGET_RATE) * TARGET_WIDTH
    if len(converted) < required_bytes:
        converted += b"\x00" * (required_bytes - len(converted))
    return converted[:required_bytes]


def extract_reference_clip(
    input_path: str | Path,
    output_path: str | Path,
    *,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
) -> ExtractionResult:
    source = Path(input_path).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()
    if source == output:
        raise ValueError("refusing to overwrite the source WAV")
    if not source.is_file():
        raise ValueError(f"source WAV does not exist: {source}")

    with wave.open(str(source), "rb") as wav_file:
        if wav_file.getcomptype() != "NONE":
            raise ValueError("source WAV must contain uncompressed PCM")
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        source_rate = wav_file.getframerate()
        frames = wav_file.readframes(wav_file.getnframes())

    mono_pcm16 = _to_pcm16_mono(frames, sample_width, channels)
    if (start_seconds is None) != (end_seconds is None):
        raise ValueError("manual range requires both start and end seconds")
    if start_seconds is None:
        selection = select_best_window(mono_pcm16, source_rate)
    else:
        selection = select_manual_range(
            mono_pcm16,
            source_rate,
            start_seconds,
            end_seconds,
        )
    normalized = _resample_exact(selection.pcm, source_rate)
    frame_count = len(normalized) // TARGET_WIDTH

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".wav", prefix=f".{output.stem}-", dir=output.parent, delete=False
        ) as temporary:
            temporary_name = temporary.name
        with wave.open(temporary_name, "wb") as wav_file:
            wav_file.setnchannels(TARGET_CHANNELS)
            wav_file.setsampwidth(TARGET_WIDTH)
            wav_file.setframerate(TARGET_RATE)
            wav_file.writeframes(normalized)
        os.replace(temporary_name, output)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return ExtractionResult(
        input_path=source,
        output_path=output,
        start_seconds=selection.start_seconds,
        rms=selection.rms,
        near_silence_ratio=selection.near_silence_ratio,
        sample_rate=TARGET_RATE,
        channels=TARGET_CHANNELS,
        sample_width=TARGET_WIDTH,
        frame_count=frame_count,
        duration_seconds=frame_count / TARGET_RATE,
        sha256=digest,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Source PCM WAV")
    parser.add_argument("--output", required=True, type=Path, help="Candidate WAV to create")
    parser.add_argument(
        "--start-seconds",
        type=float,
        help="Approved complete-utterance start; requires --end-seconds",
    )
    parser.add_argument(
        "--end-seconds",
        type=float,
        help="Approved complete-utterance end (12 seconds maximum); requires --start-seconds",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = extract_reference_clip(
            args.input,
            args.output,
            start_seconds=args.start_seconds,
            end_seconds=args.end_seconds,
        )
    except (OSError, ValueError, wave.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"output: {result.output_path}")
    print(f"selected_start_seconds: {result.start_seconds:.3f}")
    print(f"selected_rms: {result.rms}")
    print(f"near_silence_ratio: {result.near_silence_ratio:.6f}")
    print(
        "format: "
        f"{result.sample_rate} Hz, {result.sample_width * 8}-bit, "
        f"{result.channels} channel, {result.duration_seconds:.6f} s"
    )
    print(f"sha256: {result.sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
