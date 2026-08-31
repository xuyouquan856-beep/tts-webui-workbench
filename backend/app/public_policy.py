"""Public-release defaults that must stay safe on a clean installation."""

import json
from typing import Any


APP_VERSION = "0.1.0"

PUBLIC_CORS_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://tauri.localhost",
    "https://tauri.localhost",
]


def build_default_model_specs(*, has_boson_key: bool) -> list[dict[str, Any]]:
    """Return first-run model examples without enabling unconfigured providers."""

    return [
        {
            "name": "Dummy Beep Generator (Ready)",
            "provider_type": "dummy",
            "enabled": True,
            "output_format": "wav",
            "params_json": "{}",
        },
        {
            "name": "Higgs TTS 3 (Boson AI)",
            "provider_type": "higgs_api",
            "api_base": "https://api.boson.ai/v1/audio/speech",
            "model_name": "higgs-audio-v3-tts",
            "enabled": has_boson_key,
            "output_format": "mp3",
            "params_json": "{}",
        },
        {
            "name": "Local HTTP Model Example",
            "provider_type": "local_http",
            "api_base": "http://127.0.0.1:8000/v1/audio/speech",
            "model_name": "gpt-sovits-model",
            "enabled": False,
            "output_format": "wav",
            "params_json": json.dumps({"payload_mode": "openai_audio_speech"}),
        },
        {
            "name": "Local Command Execution Example",
            "provider_type": "local_command",
            "command_template": (
                'python infer.py --text "{text}" --out "{output_path}" '
                '--model "{model_path}"'
            ),
            "model_path": "data/models/voice.pth",
            "enabled": False,
            "output_format": "wav",
            "params_json": "{}",
        },
        {
            "name": "Piper TTS ONNX Example",
            "provider_type": "piper",
            "api_base": "piper",
            "model_path": "data/models/en_US-lessac-medium.onnx",
            "enabled": False,
            "output_format": "wav",
            "params_json": "{}",
        },
    ]


def build_health_payload(*, has_boson_key: bool) -> dict[str, object]:
    """Return non-sensitive diagnostics suitable for the public API."""

    return {
        "status": "healthy",
        "version": APP_VERSION,
        "boson_api_key_configured": has_boson_key,
    }
