import os
import base64
import httpx
from typing import Dict, Any
from app.providers.base import BaseTTSProvider, ProviderRequest, ProviderResult

class LocalHttpProvider(BaseTTSProvider):
    async def generate(self, request: ProviderRequest, output_path: str) -> ProviderResult:
        api_base = request.model_properties.get("api_base")
        if not api_base:
            raise ValueError("Local HTTP Provider requires 'api_base' to be configured.")
            
        model_name = request.model_properties.get("model_name")
        
        # Get payload mode, default to 'openai_audio_speech'
        payload_mode = request.params.get("payload_mode") or request.model_properties.get("payload_mode") or "openai_audio_speech"
        
        # Resolve voice profile configuration
        voice_name = None
        ref_audio_path = None
        ref_text = None
        if request.profile_config:
            voice_name = request.profile_config.get("name")
            ref_audio_path = request.profile_config.get("ref_audio_path")
            ref_text = request.profile_config.get("ref_text")
            
        # Build JSON Payload
        if payload_mode == "openai_audio_speech":
            json_payload = {
                "model": model_name,
                "input": request.text,
                "voice": voice_name or "default",
                "response_format": request.return_format,
            }
            # Add optional extra parameters
            for k, v in request.params.items():
                if k not in ["payload_mode"]:
                    json_payload[k] = v
        else:
            # generic_json payload mode
            json_payload = {
                "text": request.text,
                "model": model_name,
                "voice": voice_name,
                "params": {k: v for k, v in request.params.items() if k != "payload_mode"},
                "ref_audio_path": ref_audio_path,
                "ref_text": ref_text
            }
            
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(api_base, json=json_payload)
            
            if response.status_code != 200:
                raise RuntimeError(
                    f"Local HTTP service request failed with status code {response.status_code}."
                )
                
            # Check content-type of response
            content_type = response.headers.get("content-type", "").lower()
            
            if "application/json" in content_type:
                # Parse JSON for base64 audio or audio_url
                res_data = response.json()
                
                # Check known keys: base64_audio, audio (which could be base64), audio_url
                audio_data = None
                if "base64_audio" in res_data:
                    audio_data = base64.b64decode(res_data["base64_audio"])
                elif "audio" in res_data:
                    # check if the "audio" key is a base64 encoded string or a URL
                    val = res_data["audio"]
                    if isinstance(val, str):
                        if val.startswith("http://") or val.startswith("https://"):
                            # It's a URL, fetch it
                            audio_response = await client.get(val)
                            if audio_response.status_code == 200:
                                audio_data = audio_response.content
                        else:
                            # Try base64 decoding
                            try:
                                audio_data = base64.b64decode(val)
                            except Exception:
                                pass
                elif "audio_url" in res_data:
                    url = res_data["audio_url"]
                    audio_response = await client.get(url)
                    if audio_response.status_code == 200:
                        audio_data = audio_response.content
                        
                if audio_data is None:
                    raise RuntimeError(
                        f"Could not extract audio data from JSON response. Keys received: {list(res_data.keys())}"
                    )
                    
                with open(output_path, "wb") as out_file:
                    out_file.write(audio_data)
            else:
                # Treat response as binary audio bytes
                with open(output_path, "wb") as out_file:
                    out_file.write(response.content)
                    
        return ProviderResult(
            audio_path=output_path,
            format=request.return_format,
            metadata={
                "provider": "local_http",
                "payload_mode": payload_mode,
                "model": model_name
            }
        )
