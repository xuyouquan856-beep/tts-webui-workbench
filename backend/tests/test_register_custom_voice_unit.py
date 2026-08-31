import asyncio
import base64
import contextlib
import hashlib
import io
import importlib
import json
import os
import re
import sqlite3
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock


def write_candidate(path: Path, sample: int = 1000) -> None:
    frames = struct.pack("<h", sample) * (12 * 24_000)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24_000)
        wav_file.writeframes(frames)


def create_database(path: Path, default_params_json='{"temperature": 0.8}') -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE profiles ("
        "id INTEGER PRIMARY KEY, name TEXT, ref_audio_path TEXT, ref_text TEXT, "
        "default_params_json TEXT)"
    )
    connection.execute(
        "INSERT INTO profiles VALUES (?, ?, ?, ?, ?)",
        (6, "月代雪", "original.wav", None, default_params_json),
    )
    connection.commit()
    connection.close()


class RegisterCustomVoiceTests(unittest.TestCase):
    def setUp(self):
        try:
            self.registration = importlib.import_module("register_custom_voice")
        except ImportError as exc:
            self.fail(f"registration CLI module is missing: {exc}")

    def test_mask_voice_id_never_returns_full_identifier(self):
        voice_id = "voice_abcdef89"

        masked = self.registration.mask_voice_id(voice_id)

        self.assertEqual(masked, "voice_ab…89")
        self.assertNotEqual(masked, voice_id)
        self.assertNotIn("cdef", masked)

    def test_mask_voice_id_hides_a_character_for_every_nonempty_length(self):
        for voice_id in ("v", "vo", "voice", "123456789", "1234567890", "voice_abcdef89"):
            with self.subTest(voice_id=voice_id):
                masked = self.registration.mask_voice_id(voice_id)
                self.assertNotEqual(masked, voice_id)
                self.assertNotIn(voice_id, masked)
                visible_characters = sum(character not in "…•" for character in masked)
                self.assertLess(visible_characters, len(voice_id))

    def test_load_transcript_refuses_missing_and_empty_files(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.txt"
            empty = Path(directory) / "empty.txt"
            empty.write_text("  \n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "transcript"):
                self.registration.load_transcript(missing)
            with self.assertRaisesRegex(ValueError, "transcript"):
                self.registration.load_transcript(empty)

    def test_load_transcript_accepts_utf8_bom_and_rejects_no_meaningful_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid = root / "valid.txt"
            bom_only = root / "bom-only.txt"
            controls_only = root / "controls-only.txt"
            valid.write_bytes(b"\xef\xbb\xbf" + "月代雪の台詞".encode("utf-8"))
            bom_only.write_bytes(b"\xef\xbb\xbf   \r\n")
            controls_only.write_text("\u200b\ufeff\n", encoding="utf-8")

            self.assertEqual(self.registration.load_transcript(valid), "月代雪の台詞")
            for invalid in (bom_only, controls_only):
                with self.subTest(path=invalid):
                    with self.assertRaisesRegex(ValueError, "meaningful"):
                        self.registration.load_transcript(invalid)

    def test_validate_candidate_requires_exact_format_and_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            valid = Path(directory) / "valid.wav"
            invalid = Path(directory) / "invalid.wav"
            write_candidate(valid)
            with wave.open(str(invalid), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16_000)
                wav_file.writeframes(struct.pack("<h", 1000) * (12 * 16_000))

            details = self.registration.validate_candidate(valid)
            self.assertEqual(details["duration_seconds"], 12.0)
            with self.assertRaisesRegex(ValueError, "24 kHz"):
                self.registration.validate_candidate(invalid)

    def test_dry_run_loads_profile_without_cloud_backup_or_database_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "workbench.db"
            candidate = root / "candidate.wav"
            transcript = root / "transcript.txt"
            backup = root / "backup.json"
            create_database(database)
            write_candidate(candidate)
            transcript.write_text("これは承認済みの台詞です。", encoding="utf-8")
            before = database.read_bytes()

            result = self.registration.prepare_registration(
                database_path=database,
                audio_path=candidate,
                transcript_path=transcript,
                profile_id=6,
                backup_path=backup,
            )

            self.assertEqual(result.profile_name, "月代雪")
            self.assertEqual(result.ref_text, "これは承認済みの台詞です。")
            self.assertEqual(result.audio_bytes, candidate.read_bytes())
            self.assertEqual(len(result.audio_sha256), 64)
            self.assertNotIn("RIFF", repr(result))
            self.assertEqual(database.read_bytes(), before)
            self.assertFalse(backup.exists())

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.registration.print_dry_run(result)
            self.assertIn(result.audio_sha256, output.getvalue())

    def test_backup_preserves_all_profile_fields_and_updated_params_add_voice(self):
        original = self.registration.ProfileSnapshot(
            profile_id=6,
            profile_name="月代雪",
            default_params_json='{"temperature": 0.8}',
            ref_audio_path="original.wav",
            ref_text=None,
        )

        backup = self.registration.backup_payload(original)
        updated = self.registration.params_with_voice(
            original.default_params_json, "voice_abcdef89"
        )

        self.assertEqual(
            backup,
            {
                "profile_id": 6,
                "name": "月代雪",
                "default_params_json": '{"temperature": 0.8}',
                "ref_audio_path": "original.wav",
                "ref_text": None,
            },
        )
        self.assertEqual(json.loads(updated), {"temperature": 0.8, "voice": "voice_abcdef89"})

    def test_profile_snapshot_and_backup_preserve_null_and_empty_params_exactly(self):
        for stored_value in (None, ""):
            with self.subTest(stored_value=stored_value), tempfile.TemporaryDirectory() as directory:
                database = Path(directory) / "workbench.db"
                create_database(database, stored_value)

                profile = self.registration.load_profile(database)

                self.assertEqual(profile.default_params_json, stored_value)
                self.assertEqual(
                    self.registration.backup_payload(profile)["default_params_json"],
                    stored_value,
                )
                self.assertEqual(
                    json.loads(
                        self.registration.params_with_voice(
                            profile.default_params_json, "voice_abcdef89"
                        )
                    ),
                    {"voice": "voice_abcdef89"},
                )

    def test_write_backup_preserves_profile_fields_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "workbench.db"
            candidate = root / "candidate.wav"
            transcript = root / "transcript.txt"
            backup = root / "backup.json"
            create_database(database, None)
            write_candidate(candidate)
            transcript.write_text("承認済み台詞", encoding="utf-8")
            preparation = self.registration.prepare_registration(
                database_path=database,
                audio_path=candidate,
                transcript_path=transcript,
                backup_path=backup,
            )

            self.registration.write_backup(preparation)

            self.assertEqual(
                json.loads(backup.read_text(encoding="utf-8")),
                {
                    "profile_id": 6,
                    "name": "月代雪",
                    "default_params_json": None,
                    "ref_audio_path": "original.wav",
                    "ref_text": None,
                },
            )
            with self.assertRaises(FileExistsError):
                self.registration.write_backup(preparation)

    def test_cli_apply_requires_valid_expected_sha256_before_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "workbench.db"
            candidate = root / "candidate.wav"
            transcript = root / "transcript.txt"
            backup = root / "backup.json"
            create_database(database)
            write_candidate(candidate)
            transcript.write_text("承認済み台詞", encoding="utf-8")
            before = database.read_bytes()
            base_args = [
                "--database", str(database),
                "--audio", str(candidate),
                "--transcript", str(transcript),
                "--backup", str(backup),
                "--apply",
            ]

            for expected, marker in ((None, "--expected-sha256"), ("not-a-hash", "64-hex")):
                with self.subTest(expected=expected):
                    arguments = list(base_args)
                    if expected is not None:
                        arguments.extend(["--expected-sha256", expected])
                    errors = io.StringIO()
                    with contextlib.redirect_stderr(errors):
                        result = self.registration.main(arguments)
                    self.assertEqual(result, 2)
                    self.assertIn(marker, errors.getvalue())
                    self.assertFalse(backup.exists())
                    self.assertEqual(database.read_bytes(), before)

    def test_cli_binds_apply_to_hash_from_separate_dry_run_invocation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "workbench.db"
            candidate = root / "candidate.wav"
            transcript = root / "transcript.txt"
            backup = root / "backup.json"
            create_database(database)
            write_candidate(candidate, sample=1000)
            transcript.write_text("承認済み台詞", encoding="utf-8")
            base_args = [
                "--database", str(database),
                "--audio", str(candidate),
                "--transcript", str(transcript),
                "--backup", str(backup),
            ]

            dry_output = io.StringIO()
            with contextlib.redirect_stdout(dry_output):
                self.assertEqual(self.registration.main(base_args), 0)
            match = re.search(r"candidate_sha256: ([0-9a-f]{64})", dry_output.getvalue())
            self.assertIsNotNone(match)
            approved_hash_a = match.group(1)

            write_candidate(candidate, sample=2000)
            current_hash_b = hashlib.sha256(candidate.read_bytes()).hexdigest()
            self.assertNotEqual(current_hash_b, approved_hash_a)
            database_before = database.read_bytes()

            apply_mock = mock.AsyncMock(return_value="voice_abcdef89")
            with mock.patch.object(self.registration, "apply_registration", apply_mock), mock.patch.dict(
                os.environ, {"BOSON_API_KEY": "test-key"}
            ):
                errors = io.StringIO()
                with contextlib.redirect_stderr(errors):
                    mismatch_result = self.registration.main(
                        base_args
                        + ["--apply", "--expected-sha256", approved_hash_a.upper()]
                    )
                self.assertEqual(mismatch_result, 2)
                self.assertIn("does not match", errors.getvalue())
                apply_mock.assert_not_awaited()
                self.assertFalse(backup.exists())
                self.assertEqual(database.read_bytes(), database_before)

                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    matching_result = self.registration.main(
                        base_args
                        + ["--apply", "--expected-sha256", current_hash_b.upper()]
                    )
                self.assertEqual(matching_result, 0)
                apply_mock.assert_awaited_once()
                self.assertEqual(
                    apply_mock.await_args.kwargs["expected_sha256"], current_hash_b
                )

    def test_update_profile_succeeds_against_prepared_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "workbench.db"
            candidate = root / "candidate.wav"
            transcript = root / "transcript.txt"
            create_database(database)
            write_candidate(candidate)
            transcript.write_text("承認済み台詞", encoding="utf-8")
            preparation = self.registration.prepare_registration(
                database_path=database,
                audio_path=candidate,
                transcript_path=transcript,
            )

            self.registration.update_profile(preparation, "voice_abcdef89")

            connection = sqlite3.connect(database)
            row = connection.execute(
                "SELECT default_params_json, ref_audio_path, ref_text FROM profiles WHERE id=6"
            ).fetchone()
            connection.close()
            self.assertEqual(json.loads(row[0])["voice"], "voice_abcdef89")
            self.assertEqual(row[1], str(candidate.resolve()))
            self.assertEqual(row[2], "承認済み台詞")

    def test_update_profile_refuses_changed_snapshot_and_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "workbench.db"
            candidate = root / "candidate.wav"
            transcript = root / "transcript.txt"
            create_database(database)
            write_candidate(candidate)
            transcript.write_text("承認済み台詞", encoding="utf-8")
            preparation = self.registration.prepare_registration(
                database_path=database,
                audio_path=candidate,
                transcript_path=transcript,
            )
            connection = sqlite3.connect(database)
            connection.execute(
                "UPDATE profiles SET ref_text=? WHERE id=6", ("concurrent change",)
            )
            connection.commit()
            connection.close()

            with self.assertRaisesRegex(RuntimeError, "changed"):
                self.registration.update_profile(preparation, "voice_abcdef89")

            connection = sqlite3.connect(database)
            row = connection.execute(
                "SELECT default_params_json, ref_audio_path, ref_text FROM profiles WHERE id=6"
            ).fetchone()
            connection.close()
            self.assertEqual(row, ('{"temperature": 0.8}', "original.wav", "concurrent change"))


class FakeResponse:
    def __init__(self, status_code=201, payload=None):
        self.status_code = status_code
        self.payload = payload if payload is not None else {"voice_id": "voice_abcdef89"}

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, response=None):
        self.response = response or FakeResponse()
        self.calls = []

    async def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.response


class ApplyRegistrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.registration = importlib.import_module("register_custom_voice")
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database = self.root / "workbench.db"
        self.candidate = self.root / "candidate.wav"
        self.transcript = self.root / "transcript.txt"
        self.backup = self.root / "backup.json"
        create_database(self.database)
        write_candidate(self.candidate)
        self.transcript.write_text("承認済み台詞", encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def prepare(self):
        return self.registration.prepare_registration(
            database_path=self.database,
            audio_path=self.candidate,
            transcript_path=self.transcript,
            backup_path=self.backup,
        )

    async def test_apply_uploads_captured_bytes_and_updates_temp_database(self):
        preparation = self.prepare()
        client = FakeClient()

        voice_id = await self.registration.apply_registration(
            preparation,
            api_base="https://api.boson.ai/v1",
            api_key="test-key",
            title="月代雪",
            expected_sha256=preparation.audio_sha256,
            client=client,
        )

        self.assertEqual(voice_id, "voice_abcdef89")
        self.assertEqual(
            client.calls[0]["json"]["ref_audio"],
            base64.b64encode(preparation.audio_bytes).decode("ascii"),
        )
        connection = sqlite3.connect(self.database)
        row = connection.execute(
            "SELECT default_params_json, ref_audio_path, ref_text FROM profiles WHERE id=6"
        ).fetchone()
        connection.close()
        self.assertEqual(json.loads(row[0])["voice"], voice_id)
        self.assertEqual(row[1], str(self.candidate.resolve()))
        self.assertEqual(row[2], "承認済み台詞")
        self.assertTrue(self.backup.is_file())

    async def test_apply_rejects_changed_candidate_before_backup_or_cloud(self):
        preparation = self.prepare()
        self.candidate.write_bytes(b"changed after approval")
        client = FakeClient()

        with self.assertRaisesRegex(RuntimeError, "candidate.*changed"):
            await self.registration.apply_registration(
                preparation,
                api_base="https://api.boson.ai/v1",
                api_key="test-key",
                title="月代雪",
                expected_sha256=preparation.audio_sha256,
                client=client,
            )

        self.assertFalse(self.backup.exists())
        self.assertEqual(client.calls, [])

    async def test_cloud_failure_leaves_temp_database_unchanged(self):
        preparation = self.prepare()
        before = self.database.read_bytes()
        client = FakeClient(FakeResponse(status_code=500, payload={"error": {"type": "server_error"}}))

        with self.assertRaisesRegex(RuntimeError, "500"):
            await self.registration.apply_registration(
                preparation,
                api_base="https://api.boson.ai/v1",
                api_key="test-key",
                title="月代雪",
                expected_sha256=preparation.audio_sha256,
                client=client,
            )

        self.assertEqual(self.database.read_bytes(), before)
        self.assertTrue(self.backup.is_file())


if __name__ == "__main__":
    unittest.main()
