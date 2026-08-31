import hashlib
import importlib
import struct
import tempfile
import unittest
import wave
from pathlib import Path


def pcm16(*samples: int) -> bytes:
    return struct.pack(f"<{len(samples)}h", *samples)


class ExtractReferenceClipTests(unittest.TestCase):
    def setUp(self):
        try:
            self.extractor = importlib.import_module("tools.extract_reference_clip")
        except ImportError as exc:
            self.fail(f"extractor module is missing: {exc}")

    def test_selects_highest_rms_eligible_window_on_250ms_grid(self):
        rate = 4
        samples = [1000] * rate + [4000] * (12 * rate)

        selection = self.extractor.select_best_window(pcm16(*samples), rate)

        self.assertEqual(selection.start_frame, rate)
        self.assertEqual(selection.start_seconds, 1.0)
        self.assertEqual(selection.pcm, pcm16(*([4000] * (12 * rate))))

    def test_equal_rms_windows_choose_earliest_start(self):
        rate = 4
        samples = [2000] * (13 * rate)

        selection = self.extractor.select_best_window(pcm16(*samples), rate)

        self.assertEqual(selection.start_frame, 0)

    def test_rejects_a_window_containing_clipped_samples(self):
        rate = 4
        samples = [2000] * (12 * rate)
        samples[-1] = 32767

        with self.assertRaisesRegex(ValueError, "eligible"):
            self.extractor.select_best_window(pcm16(*samples), rate)

    def test_rejects_more_than_twenty_percent_near_silence(self):
        rate = 4
        samples = [0] * 10 + [2000] * (12 * rate - 10)

        with self.assertRaisesRegex(ValueError, "eligible"):
            self.extractor.select_best_window(pcm16(*samples), rate)

    def test_exactly_twenty_percent_near_silence_is_eligible(self):
        rate = 5
        samples = [0] * 12 + [2000] * (12 * rate - 12)

        selection = self.extractor.select_best_window(pcm16(*samples), rate)

        self.assertEqual(selection.near_silence_ratio, 0.2)

    def test_low_level_nonzero_samples_are_not_misclassified_as_silence(self):
        rate = 4
        samples = [32] * (12 * rate)

        selection = self.extractor.select_best_window(pcm16(*samples), rate)

        self.assertEqual(selection.near_silence_ratio, 0.0)

    def test_extracts_exact_24khz_16bit_mono_twelve_second_wav(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.wav"
            output = Path(directory) / "candidate.wav"
            frames = pcm16(*([1200] * (13 * 48_000)))
            with wave.open(str(source), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(48_000)
                wav_file.writeframes(frames)
            source_hash = hashlib.sha256(source.read_bytes()).hexdigest()

            result = self.extractor.extract_reference_clip(source, output)

            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), source_hash)
            with wave.open(str(output), "rb") as wav_file:
                self.assertEqual(wav_file.getnchannels(), 1)
                self.assertEqual(wav_file.getsampwidth(), 2)
                self.assertEqual(wav_file.getframerate(), 24_000)
                self.assertEqual(wav_file.getnframes(), 12 * 24_000)
                self.assertEqual(wav_file.getcomptype(), "NONE")
            self.assertEqual(result.duration_seconds, 12.0)

    def test_manual_complete_utterance_range_is_padded_to_twelve_seconds(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.wav"
            output = Path(directory) / "candidate.wav"
            rate = 24_000
            with wave.open(str(source), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(rate)
                wav_file.writeframes(pcm16(*([1200] * (13 * rate))))

            result = self.extractor.extract_reference_clip(
                source,
                output,
                start_seconds=0.5,
                end_seconds=12.25,
            )

            self.assertEqual(result.start_seconds, 0.5)
            with wave.open(str(output), "rb") as wav_file:
                frames = wav_file.readframes(wav_file.getnframes())
                self.assertEqual(wav_file.getnframes(), 12 * rate)
            samples = struct.unpack(f"<{len(frames) // 2}h", frames)
            self.assertEqual(samples[0], 1200)
            self.assertEqual(samples[(11 * rate)], 1200)
            self.assertEqual(samples[-1], 0)

    def test_refuses_to_overwrite_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.wav"
            with wave.open(str(source), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(24_000)
                wav_file.writeframes(pcm16(*([1000] * (12 * 24_000))))

            with self.assertRaisesRegex(ValueError, "overwrite"):
                self.extractor.extract_reference_clip(source, source)


if __name__ == "__main__":
    unittest.main()
