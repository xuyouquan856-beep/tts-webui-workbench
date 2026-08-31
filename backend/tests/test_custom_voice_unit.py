import base64
import importlib
import tempfile
import unittest
from pathlib import Path


class FakeResponse:
    def __init__(self, status_code=201, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"voice_id": "voice_abcdef89"}

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, response=None):
        self.response = response or FakeResponse()
        self.calls = []

    async def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.response


class FailingClient:
    async def post(self, url, **kwargs):
        raise RuntimeError("secret-key and secret-audio leaked by transport")


class CustomVoiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        try:
            self.service = importlib.import_module("app.services.custom_voice")
        except ImportError as exc:
            self.fail(f"custom voice service is missing: {exc}")

    async def test_posts_base64_audio_and_returns_trimmed_voice_id(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "candidate.wav"
            audio.write_bytes(b"RIFF-private-audio")
            client = FakeClient(FakeResponse(payload={"voice_id": "  voice_abcdef89  "}))

            voice_id = await self.service.create_custom_voice(
                client,
                "https://api.boson.ai/v1/",
                "private-key",
                str(audio),
                "月代雪の台詞",
                "月代雪",
            )

            self.assertEqual(voice_id, "voice_abcdef89")
            call = client.calls[0]
            self.assertEqual(call["url"], "https://api.boson.ai/v1/audio/voices")
            self.assertEqual(call["headers"], {"Authorization": "Bearer private-key"})
            self.assertEqual(
                call["json"],
                {
                    "ref_audio": base64.b64encode(b"RIFF-private-audio").decode("ascii"),
                    "ref_text": "月代雪の台詞",
                    "title": "月代雪",
                },
            )

    async def test_failure_reports_status_and_safe_error_type_only(self):
        client = FakeClient(
            FakeResponse(
                status_code=422,
                payload={"error": {"type": "invalid_reference", "message": "private details"}},
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "candidate.wav"
            audio.write_bytes(b"secret-audio")

            with self.assertRaises(RuntimeError) as raised:
                await self.service.create_custom_voice(
                    client,
                    "https://api.boson.ai/v1",
                    "secret-key",
                    str(audio),
                    "秘密の台詞",
                    "月代雪",
                )

        message = str(raised.exception)
        self.assertIn("422", message)
        self.assertIn("invalid_reference", message)
        self.assertNotIn("secret-key", message)
        self.assertNotIn("secret-audio", message)
        self.assertNotIn("private details", message)

    async def test_unsafe_error_types_are_never_echoed(self):
        unsafe_types = (
            "invalid\nAuthorization-secret",
            "sk_live_SUPERSECRET",
            "voice_1234567890abcdef",
            "秘密の識別子",
            "x" * 65,
        )
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "candidate.wav"
            audio.write_bytes(b"audio")
            for unsafe_type in unsafe_types:
                with self.subTest(unsafe_type=unsafe_type):
                    client = FakeClient(
                        FakeResponse(
                            status_code=422,
                            payload={"error": {"type": unsafe_type}},
                        )
                    )
                    with self.assertRaises(RuntimeError) as raised:
                        await self.service.create_custom_voice(
                            client,
                            "https://api.boson.ai/v1",
                            "key",
                            str(audio),
                            "台詞",
                            "月代雪",
                        )
                    self.assertEqual(
                        str(raised.exception),
                        "Boson voice creation failed (422)",
                    )

    async def test_provided_audio_bytes_are_uploaded_without_rereading_path(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "candidate.wav"
            audio.write_bytes(b"mutated-path-bytes")
            approved_bytes = b"approved-candidate-bytes"
            client = FakeClient()

            await self.service.create_custom_voice(
                client,
                "https://api.boson.ai/v1",
                "key",
                str(audio),
                "台詞",
                "月代雪",
                audio_bytes=approved_bytes,
            )

            self.assertEqual(
                client.calls[0]["json"]["ref_audio"],
                base64.b64encode(approved_bytes).decode("ascii"),
            )

    async def test_rejects_response_without_nonempty_voice_id(self):
        client = FakeClient(FakeResponse(payload={"voice_id": "  "}))
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "candidate.wav"
            audio.write_bytes(b"audio")

            with self.assertRaisesRegex(RuntimeError, "no voice_id"):
                await self.service.create_custom_voice(
                    client,
                    "https://api.boson.ai/v1",
                    "key",
                    str(audio),
                    "台詞",
                    "月代雪",
                )

    async def test_transport_failure_is_sanitized(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "candidate.wav"
            audio.write_bytes(b"secret-audio")

            with self.assertRaises(RuntimeError) as raised:
                await self.service.create_custom_voice(
                    FailingClient(),
                    "https://api.boson.ai/v1",
                    "secret-key",
                    str(audio),
                    "台詞",
                    "月代雪",
                )

        message = str(raised.exception)
        self.assertIn("request failed", message)
        self.assertNotIn("secret-key", message)
        self.assertNotIn("secret-audio", message)


if __name__ == "__main__":
    unittest.main()
