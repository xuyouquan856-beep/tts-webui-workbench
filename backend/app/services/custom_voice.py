"""Boson custom-voice registration service."""

from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any


_SAFE_ERROR_TYPE = re.compile(r"[a-z][a-z0-9_.-]{0,63}\Z", re.ASCII)
_SENSITIVE_ERROR_FRAGMENTS = (
    "authorization",
    "bearer",
    "credential",
    "secret",
    "token",
    "voice_",
    "sk_",
)


def _safe_error_type(response: Any) -> str | None:
    try:
        payload = response.json()
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if isinstance(error, dict):
        error_type = error.get("type")
    else:
        error_type = payload.get("type")
    if not isinstance(error_type, str):
        return None
    token = error_type.strip()
    if not _SAFE_ERROR_TYPE.fullmatch(token):
        return None
    if any(fragment in token for fragment in _SENSITIVE_ERROR_FRAGMENTS):
        return None
    if token:
        return token
    return None


async def create_custom_voice(
    client,
    api_base: str,
    api_key: str,
    audio_path: str,
    ref_text: str,
    title: str,
    *,
    audio_bytes: bytes | None = None,
) -> str:
    source_bytes = bytes(audio_bytes) if audio_bytes is not None else Path(audio_path).read_bytes()
    encoded = base64.b64encode(source_bytes).decode("ascii")
    try:
        response = await client.post(
            f"{api_base.rstrip('/')}/audio/voices",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"ref_audio": encoded, "ref_text": ref_text, "title": title},
        )
    except Exception as exc:
        raise RuntimeError(
            f"Boson voice creation request failed ({type(exc).__name__})"
        ) from None
    if response.status_code not in (200, 201):
        error_type = _safe_error_type(response)
        suffix = f", type={error_type}" if error_type else ""
        raise RuntimeError(
            f"Boson voice creation failed ({response.status_code}{suffix})"
        )
    try:
        payload = response.json()
    except Exception:
        raise RuntimeError("Boson voice creation returned invalid JSON") from None
    voice_id = payload.get("voice_id") if isinstance(payload, dict) else None
    if not isinstance(voice_id, str) or not voice_id.strip():
        raise RuntimeError("Boson voice creation returned no voice_id")
    return voice_id.strip()
