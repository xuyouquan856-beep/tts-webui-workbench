import base64
import os
import httpx
from collections.abc import AsyncIterator
from app.providers.base import BaseTTSProvider, ProviderRequest, ProviderResult
from app.config import settings
from app.services.http_client import get_http_client


VOICE_PARAM_KEYS = ("voice", "voice_id", "speaker", "preset_voice")


class HiggsApiProvider(BaseTTSProvider):
    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client if client is not None else get_http_client()

    async def _post_reference(
        self,
        api_base: str,
        headers: dict,
        model_name: str,
        text: str,
        request_params: dict,
        ref_audio_path: str,
        ref_text: str | None,
    ):
        reference_params = {**request_params}
        for key in VOICE_PARAM_KEYS:
            reference_params.pop(key, None)

        with open(ref_audio_path, "rb") as ref_audio:
            encoded_audio = base64.b64encode(ref_audio.read()).decode("ascii")

        json_data = {
            "model": model_name,
            "input": text,
            "ref_audio": encoded_audio,
            **reference_params,
        }
        if ref_text:
            json_data["ref_text"] = ref_text

        return await self.client.post(
            api_base,
            headers=headers,
            json=json_data,
        )

    async def _post_json(
        self,
        api_base: str,
        headers: dict,
        model_name: str,
        text: str,
        request_params: dict,
        ref_audio_path: str | None,
        ref_text: str | None,
    ):
        json_data = {
            "model": model_name,
            "input": text,
            **request_params,
        }
        if ref_audio_path and ref_audio_path.startswith(("http://", "https://")):
            json_data["ref_audio"] = ref_audio_path
            if ref_text:
                json_data["ref_text"] = ref_text
        return await self.client.post(api_base, headers=headers, json=json_data)

    @staticmethod
    def _safe_error_message(response) -> str | None:
        try:
            payload = response.json()
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        error = payload.get("error")
        if not isinstance(error, dict):
            return None
        message = error.get("message")
        if not isinstance(message, str):
            return None
        message = " ".join(message.split())
        return message[:300] or None

    @classmethod
    def _raise_for_status(cls, response) -> None:
        if not 200 <= response.status_code < 300:
            message = cls._safe_error_message(response)
            suffix = f" Reason: {message}" if message else ""
            raise RuntimeError(
                f"Higgs API request failed with status code "
                f"{response.status_code}.{suffix}"
            )

    async def stream_pcm(self, request: ProviderRequest) -> AsyncIterator[bytes]:
        """Yield raw PCM chunks from Higgs without buffering the upstream body."""
        api_key = request.params.get("api_key") or settings.boson_api_key or os.getenv("BOSON_API_KEY")
        if not api_key:
            raise ValueError(
                "Missing BOSON_API_KEY. Please set the BOSON_API_KEY environment variable, "
                "configure it in your .env file, or provide it in the request parameters."
            )

        api_base = request.model_properties.get("api_base") or "https://api.boson.ai/v1/audio/speech"
        model_name = request.model_properties.get("model_name") or "higgs-audio-v3-tts"
        request_params = {**request.params}
        request_params.pop("api_key", None)

        json_data = {
            "model": model_name,
            "input": request.text,
            **request_params,
            "stream": True,
            "response_format": "pcm",
        }
        explicit_voice = any(request_params.get(key) for key in VOICE_PARAM_KEYS)
        profile_ref_audio_path = (
            request.profile_config.get("ref_audio_path") if request.profile_config else None
        )
        ref_text = request.profile_config.get("ref_text") if request.profile_config else None
        if (
            not explicit_voice
            and profile_ref_audio_path
            and not profile_ref_audio_path.startswith(("http://", "https://"))
        ):
            raise ValueError(
                "Streaming PCM does not support a local reference audio without an explicit voice."
            )
        if (
            not explicit_voice
            and profile_ref_audio_path
            and profile_ref_audio_path.startswith(("http://", "https://"))
        ):
            json_data["ref_audio"] = profile_ref_audio_path
            if ref_text:
                json_data["ref_text"] = ref_text

        headers = {"Authorization": f"Bearer {api_key}"}
        async with self.client.stream("POST", api_base, headers=headers, json=json_data) as response:
            self._raise_for_status(response)
            async for chunk in response.aiter_bytes():
                if chunk:
                    yield chunk

    async def generate(self, request: ProviderRequest, output_path: str) -> ProviderResult:
        # Resolve API Key
        # Priority: params -> settings (env/.env) -> environment direct
        api_key = request.params.get("api_key") or settings.boson_api_key or os.getenv("BOSON_API_KEY")
        if not api_key:
            raise ValueError(
                "Missing BOSON_API_KEY. Please set the BOSON_API_KEY environment variable, "
                "configure it in your .env file, or provide it in the request parameters."
            )
            
        # Resolve base URL and model name
        api_base = request.model_properties.get("api_base") or "https://api.boson.ai/v1/audio/speech"
        model_name = request.model_properties.get("model_name") or "higgs-audio-v3-tts"
        
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        # Prepare parameters (exclude internally handled parameters)
        request_params = {**request.params}
        request_params.pop("api_key", None)
        
        # An explicit custom voice always wins on the first request. Keep the
        # profile reference separately so a non-auth voice failure can recover.
        profile_ref_audio_path = None
        ref_text = None
        if request.profile_config:
            profile_ref_audio_path = request.profile_config.get("ref_audio_path")
            ref_text = request.profile_config.get("ref_text")

        explicit_voice = any(request_params.get(key) for key in VOICE_PARAM_KEYS)
        ref_audio_path = None if explicit_voice else profile_ref_audio_path
        local_reference = bool(
            profile_ref_audio_path and os.path.isfile(profile_ref_audio_path)
        )
        used_reference = False

        if ref_audio_path and os.path.isfile(ref_audio_path):
            response = await self._post_reference(
                api_base,
                headers,
                model_name,
                request.text,
                request_params,
                ref_audio_path,
                ref_text,
            )
            used_reference = True
        else:
            response = await self._post_json(
                api_base,
                headers,
                model_name,
                request.text,
                request_params,
                ref_audio_path,
                ref_text,
            )
            used_reference = bool(
                ref_audio_path
                and ref_audio_path.startswith(("http://", "https://"))
            )

        if (
            explicit_voice
            and not 200 <= response.status_code < 300
            and response.status_code not in (401, 403)
            and local_reference
        ):
            response = await self._post_reference(
                api_base,
                headers,
                model_name,
                request.text,
                request_params,
                profile_ref_audio_path,
                ref_text,
            )
            used_reference = True

        self._raise_for_status(response)

        with open(output_path, "wb") as out_file:
            out_file.write(response.content)

        return ProviderResult(
            audio_path=output_path,
            format=request.return_format,
            metadata={
                "provider": "higgs_api",
                "model": model_name,
                "api_base": api_base,
                "cloned": used_reference
            }
        )
