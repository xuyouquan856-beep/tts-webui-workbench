import base64
import importlib
import inspect
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from app import main
from app.providers import higgs_api
from app.providers.base import ProviderRequest
from app.providers.higgs_api import HiggsApiProvider


def fake_response(status_code=200, content=b"audio", text="", json_body=None):
    response = SimpleNamespace(status_code=status_code, content=content, text=text)
    response.json = Mock(
        return_value=json_body,
        side_effect=None if json_body is not None else ValueError("not json"),
    )
    return response


def provider_request(params, ref_audio_path):
    return ProviderRequest(
        text="落ち着いて。",
        model_properties={
            "api_base": "https://api.boson.ai/v1/audio/speech",
            "model_name": "higgs-tts-3",
        },
        profile_config={
            "ref_audio_path": ref_audio_path,
            "ref_text": "落ち着いて。",
        },
        params={"api_key": "test-key", **params},
        return_format="mp3",
    )


class FakeClient:
    def __init__(self, responses=None):
        self.calls = []
        self.responses = list(responses or [fake_response()])

    async def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        if not self.responses:
            raise AssertionError("unexpected extra HTTP request")
        return self.responses.pop(0)


class HiggsApiProviderTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        self.reference_path = temp_path / "reference.wav"
        self.reference_path.write_bytes(b"RIFF-reference")
        self.output_path = temp_path / "output.mp3"
        self.client = FakeClient()

    def tearDown(self):
        self.temp_dir.cleanup()

    def provider(self):
        self.assertIn("client", inspect.signature(HiggsApiProvider).parameters)
        return HiggsApiProvider(self.client)

    async def test_explicit_voice_uses_json_without_reference_upload(self):
        request = provider_request(
            params={"voice": "voice_test", "temperature": 0.8},
            ref_audio_path=str(self.reference_path),
        )

        await self.provider().generate(request, str(self.output_path))

        call = self.client.calls[0]
        self.assertEqual(call["json"]["voice"], "voice_test")
        self.assertNotIn("ref_audio", call["json"])
        self.assertNotIn("files", call)
        self.assertEqual(self.output_path.read_bytes(), b"audio")

    async def test_voice_id_uses_json_without_reference_upload(self):
        request = provider_request(
            params={"voice_id": "voice_test", "temperature": 0.8},
            ref_audio_path=str(self.reference_path),
        )

        await self.provider().generate(request, str(self.output_path))

        call = self.client.calls[0]
        self.assertIn("json", call)
        self.assertEqual(call["json"]["voice_id"], "voice_test")
        self.assertNotIn("files", call)

    async def test_reference_file_uses_base64_json_and_preserves_numeric_params(self):
        request = provider_request(
            params={
                "voice": "",
                "voice_id": "",
                "speaker": "",
                "preset_voice": "",
                "speed": 1.0,
                "pitch": 1.2,
                "temperature": 0.8,
            },
            ref_audio_path=str(self.reference_path),
        )

        await self.provider().generate(request, str(self.output_path))

        call = self.client.calls[0]
        payload = call["json"]
        self.assertNotIn("files", call)
        self.assertNotIn("data", call)
        self.assertEqual(base64.b64decode(payload["ref_audio"]), b"RIFF-reference")
        self.assertEqual(payload["ref_text"], "落ち着いて。")
        self.assertIsInstance(payload["temperature"], float)
        self.assertEqual(payload["speed"], 1.0)
        self.assertEqual(payload["pitch"], 1.2)
        self.assertEqual(payload["temperature"], 0.8)
        for key in ("voice", "voice_id", "speaker", "preset_voice"):
            self.assertNotIn(key, payload)

    async def test_invalid_voice_retries_once_with_local_reference(self):
        self.client.responses = [fake_response(404), fake_response(200, b"fallback-audio")]
        request = provider_request(
            params={"voice": "voice_invalid", "speaker": "ignored-on-fallback"},
            ref_audio_path=str(self.reference_path),
        )

        result = await self.provider().generate(request, str(self.output_path))

        self.assertEqual(len(self.client.calls), 2)
        self.assertIn("json", self.client.calls[0])
        self.assertIn("json", self.client.calls[1])
        self.assertNotIn("files", self.client.calls[1])
        fallback_payload = self.client.calls[1]["json"]
        self.assertEqual(
            base64.b64decode(fallback_payload["ref_audio"]),
            b"RIFF-reference",
        )
        for key in ("voice", "voice_id", "speaker", "preset_voice"):
            self.assertNotIn(key, fallback_payload)
        self.assertEqual(self.output_path.read_bytes(), b"fallback-audio")
        self.assertTrue(result.metadata["cloned"])

    async def test_authentication_failure_does_not_retry_reference(self):
        self.client.responses = [fake_response(401, text="unauthorized")]
        request = provider_request(
            params={"voice": "voice_private"},
            ref_audio_path=str(self.reference_path),
        )

        with self.assertRaisesRegex(RuntimeError, "401") as error:
            await self.provider().generate(request, str(self.output_path))

        self.assertEqual(len(self.client.calls), 1)
        self.assertNotIn("voice_private", str(error.exception))

    async def test_boson_error_message_is_included_and_bounded(self):
        long_message = "temperature must be a number" + ("x" * 500)
        self.client.responses = [
            fake_response(
                400,
                json_body={
                    "error": {
                        "message": long_message,
                        "debug": "Bearer secret must not be exposed",
                    },
                    "request_payload": "base64 audio must not be exposed",
                },
            )
        ]
        request = provider_request(
            params={"voice": "voice_test"},
            ref_audio_path=None,
        )

        with self.assertRaises(RuntimeError) as error:
            await self.provider().generate(request, str(self.output_path))

        rendered = str(error.exception)
        self.assertIn("temperature must be a number", rendered)
        self.assertNotIn("Bearer secret", rendered)
        self.assertNotIn("base64 audio", rendered)
        self.assertLessEqual(len(rendered), 400)

    async def test_failed_reference_fallback_is_not_retried(self):
        self.client.responses = [fake_response(404), fake_response(500)]
        request = provider_request(
            params={"voice": "voice_invalid"},
            ref_audio_path=str(self.reference_path),
        )

        with self.assertRaisesRegex(RuntimeError, "500"):
            await self.provider().generate(request, str(self.output_path))

        self.assertEqual(len(self.client.calls), 2)

    async def test_missing_reference_file_does_not_trigger_fallback(self):
        self.client.responses = [fake_response(404)]
        missing_reference = Path(self.temp_dir.name) / "missing.wav"
        request = provider_request(
            params={"voice": "voice_invalid"},
            ref_audio_path=str(missing_reference),
        )

        with self.assertRaisesRegex(RuntimeError, "404"):
            await self.provider().generate(request, str(self.output_path))

        self.assertEqual(len(self.client.calls), 1)

    async def test_default_provider_uses_shared_client(self):
        self.assertTrue(hasattr(higgs_api, "get_http_client"))
        request = provider_request(params={"voice": "voice_test"}, ref_audio_path=None)

        with patch.object(higgs_api, "get_http_client", return_value=self.client):
            await HiggsApiProvider().generate(request, str(self.output_path))

        self.assertEqual(len(self.client.calls), 1)


class SharedHttpClientTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        try:
            self.http_client = importlib.import_module("app.services.http_client")
        except ModuleNotFoundError:
            self.http_client = None

    async def asyncTearDown(self):
        if self.http_client is not None:
            await self.http_client.close_http_client()

    def require_module(self):
        self.assertIsNotNone(self.http_client, "shared HTTP client module is missing")
        return self.http_client

    async def test_get_before_start_raises(self):
        http_client = self.require_module()
        await http_client.close_http_client()

        with self.assertRaisesRegex(RuntimeError, "has not started"):
            http_client.get_http_client()

    async def test_start_reuses_one_client(self):
        http_client = self.require_module()
        managed_client = SimpleNamespace(aclose=AsyncMock())

        with patch.object(http_client.httpx, "AsyncClient", return_value=managed_client) as constructor:
            first = await http_client.start_http_client()
            second = await http_client.start_http_client()

        self.assertIs(first, managed_client)
        self.assertIs(second, managed_client)
        constructor.assert_called_once()

    async def test_close_closes_and_clears_client(self):
        http_client = self.require_module()
        managed_client = SimpleNamespace(aclose=AsyncMock())

        with patch.object(http_client.httpx, "AsyncClient", return_value=managed_client):
            await http_client.start_http_client()
            await http_client.close_http_client()

        managed_client.aclose.assert_awaited_once()
        with self.assertRaises(RuntimeError):
            http_client.get_http_client()


class MainLifespanTests(unittest.IsolatedAsyncioTestCase):
    async def test_lifespan_starts_and_closes_shared_client_around_existing_startup(self):
        self.assertTrue(hasattr(main, "start_http_client"))
        self.assertTrue(hasattr(main, "close_http_client"))
        fake_db = SimpleNamespace(close=Mock())
        events = []

        async def start_client():
            events.append("http-start")

        async def close_client():
            events.append("http-close")

        async def worker():
            await __import__("asyncio").Event().wait()

        with (
            patch.object(main.Base.metadata, "create_all") as create_all,
            patch.object(main, "SessionLocal", return_value=fake_db),
            patch.object(main, "seed_database") as seed_database,
            patch.object(main, "queue_worker_loop", side_effect=worker),
            patch.object(main, "start_http_client", side_effect=start_client) as start,
            patch.object(main, "close_http_client", side_effect=close_client) as close,
        ):
            async with main.lifespan(SimpleNamespace()):
                self.assertEqual(events, ["http-start"])
                close.assert_not_awaited()

        self.assertEqual(events, ["http-start", "http-close"])
        start.assert_awaited_once()
        close.assert_awaited_once()
        create_all.assert_called_once_with(bind=main.engine)
        seed_database.assert_called_once_with(fake_db)
        fake_db.close.assert_called_once()

    async def test_lifespan_closes_shared_client_when_worker_fails(self):
        fake_db = SimpleNamespace(close=Mock())
        close_client = AsyncMock()

        async def failing_worker():
            raise RuntimeError("worker failed")

        with (
            patch.object(main.Base.metadata, "create_all"),
            patch.object(main, "SessionLocal", return_value=fake_db),
            patch.object(main, "seed_database"),
            patch.object(main, "queue_worker_loop", side_effect=failing_worker),
            patch.object(main, "start_http_client", new_callable=AsyncMock),
            patch.object(main, "close_http_client", close_client),
        ):
            with self.assertRaisesRegex(RuntimeError, "worker failed"):
                async with main.lifespan(SimpleNamespace()):
                    await __import__("asyncio").sleep(0)

        close_client.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
