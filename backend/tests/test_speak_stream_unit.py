import asyncio
import json
import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from app.providers.base import ProviderRequest
from app.providers.higgs_api import HiggsApiProvider
from app.routers import speak_stream
from app.schemas import SpeakRequest
from app.services.generation_service import GenerationService


class FakeQuery:
    def __init__(self, value):
        self.value = value

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.value


class FakeDatabase:
    def __init__(self, model, profile=None):
        self.model = model
        self.profile = profile

    def query(self, entity):
        if entity.__name__ == "ModelConfig":
            return FakeQuery(self.model)
        return FakeQuery(self.profile)


class StreamingResponse:
    def __init__(self, chunks, status_code=200):
        self.status_code = status_code
        self._chunks = chunks
        self.closed = False

    async def aiter_bytes(self):
        for chunk in self._chunks:
            yield chunk


class StreamContext:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, *_args):
        self.response.closed = True


class StreamingClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def stream(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        return StreamContext(self.response)


def model(provider_type="higgs_api", params_json='{"speed": 0.8}'):
    return SimpleNamespace(
        id=9,
        name="test model",
        provider_type=provider_type,
        api_base="https://api.example.test/v1/audio/speech",
        model_name="higgs-test",
        command_template=None,
        model_path=None,
        output_format="mp3",
        enabled=True,
        params_json=params_json,
    )


def profile(default_params_json='{"speed": 1.0, "voice": "profile-voice"}'):
    return SimpleNamespace(
        id=6,
        name="Yuki",
        language="ja",
        provider_type="higgs_api",
        model_id=9,
        ref_audio_path="C:/reference.wav",
        ref_text="reference transcript",
        default_params_json=default_params_json,
    )


class RequestResolutionTests(unittest.TestCase):
    def test_resolve_provider_request_merges_model_profile_and_request_params_in_order(self):
        request = GenerationService.resolve_provider_request(
            db=FakeDatabase(model(), profile()),
            text="hello",
            model_id=9,
            profile_id=6,
            params_json=json.dumps({"speed": 1.2, "voice": "request-voice"}),
            return_format="pcm",
        )

        self.assertEqual(request.params["speed"], 1.2)
        self.assertEqual(request.params["voice"], "request-voice")
        self.assertEqual(request.return_format, "pcm")
        self.assertEqual(request.model_properties["model_name"], "higgs-test")


class HiggsStreamingProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_stream_pcm_emits_only_nonempty_chunks_and_closes_response_on_cancel(self):
        response = StreamingResponse([b"first", b"", b"second"])
        client = StreamingClient(response)
        provider = HiggsApiProvider(client)
        request = ProviderRequest(
            text="hello",
            model_properties={
                "api_base": "https://api.example.test/v1/audio/speech",
                "model_name": "higgs-test",
            },
            profile_config={"ref_audio_path": "https://example.test/ref.wav"},
            params={"api_key": "test-key", "voice": "explicit-voice"},
            return_format="pcm",
        )

        stream = provider.stream_pcm(request)
        self.assertEqual(await anext(stream), b"first")
        self.assertEqual(await anext(stream), b"second")
        await stream.aclose()

        self.assertTrue(response.closed)
        self.assertEqual(client.calls[0]["method"], "POST")
        self.assertEqual(client.calls[0]["json"]["stream"], True)
        self.assertEqual(client.calls[0]["json"]["response_format"], "pcm")
        self.assertEqual(client.calls[0]["json"]["voice"], "explicit-voice")
        self.assertNotIn("ref_audio", client.calls[0]["json"])

    async def test_stream_pcm_keeps_any_explicit_voice_parameter_ahead_of_profile_reference(self):
        response = StreamingResponse([b"audio"])
        provider = HiggsApiProvider(StreamingClient(response))
        request = ProviderRequest(
            text="hello",
            model_properties={},
            profile_config={"ref_audio_path": "https://example.test/ref.wav"},
            params={"api_key": "test-key", "voice_id": "explicit-voice-id"},
            return_format="pcm",
        )

        stream = provider.stream_pcm(request)
        self.assertEqual(await anext(stream), b"audio")
        await stream.aclose()

        json_data = provider.client.calls[0]["json"]
        self.assertEqual(json_data["voice_id"], "explicit-voice-id")
        self.assertNotIn("ref_audio", json_data)

    async def test_stream_pcm_validates_upstream_status_before_yielding(self):
        response = StreamingResponse([b"audio"], status_code=503)
        provider = HiggsApiProvider(StreamingClient(response))
        request = ProviderRequest(
            text="hello",
            model_properties={},
            profile_config=None,
            params={"api_key": "test-key"},
            return_format="pcm",
        )

        with self.assertRaisesRegex(RuntimeError, "503"):
            await anext(provider.stream_pcm(request))

    async def test_stream_pcm_rejects_local_reference_without_an_explicit_voice_before_opening_upstream(self):
        client = StreamingClient(StreamingResponse([b"audio"]))
        provider = HiggsApiProvider(client)
        request = ProviderRequest(
            text="hello",
            model_properties={},
            profile_config={"ref_audio_path": "C:/reference.wav"},
            params={"api_key": "test-key"},
            return_format="pcm",
        )

        with self.assertRaisesRegex(ValueError, "local reference"):
            await anext(provider.stream_pcm(request))

        self.assertEqual(client.calls, [])


class SpeakStreamRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_non_higgs_provider_before_opening_stream(self):
        db = FakeDatabase(model(provider_type="dummy"))

        with self.assertRaises(HTTPException) as raised:
            await speak_stream.speak_stream(SpeakRequest(text="hello", model_id=9), db)

        self.assertEqual(raised.exception.status_code, 400)

    async def test_does_not_return_response_when_local_reference_has_no_explicit_voice(self):
        provider = HiggsApiProvider(StreamingClient(StreamingResponse([b"audio"])))
        original_get_provider = GenerationService.get_provider
        GenerationService.get_provider = staticmethod(lambda _provider_type: provider)
        try:
            with self.assertRaises(HTTPException) as raised:
                await speak_stream.speak_stream(
                    SpeakRequest(text="hello", model_id=9, profile_id=6),
                    FakeDatabase(model(), profile(default_params_json="{}")),
                )
        finally:
            GenerationService.get_provider = original_get_provider

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(provider.client.calls, [])

    async def test_does_not_return_response_when_upstream_status_is_not_successful(self):
        provider = HiggsApiProvider(StreamingClient(StreamingResponse([], status_code=503)))
        original_get_provider = GenerationService.get_provider
        GenerationService.get_provider = staticmethod(lambda _provider_type: provider)
        try:
            with self.assertRaises(HTTPException) as raised:
                await speak_stream.speak_stream(
                    SpeakRequest(text="hello", model_id=9), FakeDatabase(model())
                )
        finally:
            GenerationService.get_provider = original_get_provider

        self.assertEqual(raised.exception.status_code, 502)

    async def test_does_not_return_response_when_upstream_stream_is_empty(self):
        provider = HiggsApiProvider(StreamingClient(StreamingResponse([])))
        original_get_provider = GenerationService.get_provider
        GenerationService.get_provider = staticmethod(lambda _provider_type: provider)
        try:
            with self.assertRaises(HTTPException) as raised:
                await speak_stream.speak_stream(
                    SpeakRequest(text="hello", model_id=9), FakeDatabase(model())
                )
        finally:
            GenerationService.get_provider = original_get_provider

        self.assertEqual(raised.exception.status_code, 502)

    async def test_returns_pcm_headers_and_first_chunk_before_second_is_produced(self):
        first_yielded = asyncio.Event()
        allow_second = asyncio.Event()
        second_produced = asyncio.Event()

        class DelayedProvider:
            async def stream_pcm(self, _request):
                first_yielded.set()
                yield b"first"
                await allow_second.wait()
                second_produced.set()
                yield b"second"

        original_get_provider = GenerationService.get_provider
        GenerationService.get_provider = staticmethod(lambda _provider_type: DelayedProvider())
        try:
            response = await speak_stream.speak_stream(
                SpeakRequest(text="hello", model_id=9), FakeDatabase(model())
            )
            self.assertTrue(first_yielded.is_set())
            self.assertFalse(second_produced.is_set())
            iterator = response.body_iterator
            self.assertEqual(await anext(iterator), b"first")
            self.assertTrue(first_yielded.is_set())
            self.assertFalse(second_produced.is_set())
            allow_second.set()
            self.assertEqual(await anext(iterator), b"second")
            await iterator.aclose()
        finally:
            GenerationService.get_provider = original_get_provider

        self.assertEqual(response.media_type, "application/octet-stream")
        self.assertEqual(response.headers["x-audio-sample-rate"], "24000")
        self.assertEqual(response.headers["x-audio-channels"], "1")
        self.assertEqual(response.headers["x-audio-sample-format"], "s16le")

    async def test_downstream_cancellation_closes_provider_generator(self):
        closed = asyncio.Event()

        class CancellableProvider:
            async def stream_pcm(self, _request):
                try:
                    yield b"first"
                    await asyncio.Event().wait()
                finally:
                    closed.set()

        original_get_provider = GenerationService.get_provider
        GenerationService.get_provider = staticmethod(lambda _provider_type: CancellableProvider())
        try:
            response = await speak_stream.speak_stream(
                SpeakRequest(text="hello", model_id=9), FakeDatabase(model())
            )
            iterator = response.body_iterator
            self.assertEqual(await anext(iterator), b"first")
            await iterator.aclose()
        finally:
            GenerationService.get_provider = original_get_provider

        self.assertTrue(closed.is_set())


if __name__ == "__main__":
    unittest.main()
