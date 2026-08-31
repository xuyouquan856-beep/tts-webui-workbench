"""Explicit dry-run/apply command for registering the approved profile 6 clip."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import hmac
import io
import json
import os
import re
import sqlite3
import sys
import wave
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.services.custom_voice import create_custom_voice


PROFILE_ID = 6
API_BASE = "https://api.boson.ai/v1"
APP_DATA_DIR = (
    Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    / "com.tts-webui-workbench.desktop"
)
DEFAULT_DATABASE = APP_DATA_DIR / "db" / "tts_workbench.db"
DEFAULT_AUDIO = APP_DATA_DIR / "reference" / "profile_6_custom_voice.wav"
SHA256_PATTERN = re.compile(r"[0-9a-fA-F]{64}\Z", re.ASCII)


@dataclass(frozen=True)
class ProfileSnapshot:
    profile_id: int
    profile_name: str
    default_params_json: str | None
    ref_audio_path: str | None
    ref_text: str | None


@dataclass(frozen=True)
class RegistrationPreparation:
    database_path: Path
    audio_path: Path
    transcript_path: Path
    backup_path: Path
    profile: ProfileSnapshot
    ref_text: str
    audio_bytes: bytes = field(repr=False)
    audio_sha256: str
    audio_details: dict[str, int | float | str]

    @property
    def profile_name(self) -> str:
        return self.profile.profile_name


def mask_voice_id(voice_id: str) -> str:
    value = voice_id.strip()
    if not value:
        return "••••"
    if len(value) == 1:
        return "…"
    if len(value) <= 10:
        if len(value) == 2:
            return f"{value[0]}…"
        return f"{value[0]}…{value[-1]}"
    return f"{value[:8]}…{value[-2:]}"


def load_transcript(path: str | Path) -> str:
    transcript_path = Path(path)
    if not transcript_path.is_file():
        raise ValueError(f"transcript file does not exist: {transcript_path}")
    transcript = transcript_path.read_text(encoding="utf-8-sig").strip()
    if not transcript or not any(character.isalnum() for character in transcript):
        raise ValueError(
            "transcript must contain meaningful approved verbatim Japanese text"
        )
    return transcript


def validate_candidate_bytes(audio_bytes: bytes) -> dict[str, int | float | str]:
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            compression = wav_file.getcomptype()
    except wave.Error as exc:
        raise ValueError(f"candidate is not a readable PCM WAV: {exc}") from exc

    if sample_rate != 24_000:
        raise ValueError("candidate WAV must be 24 kHz")
    if sample_width != 2:
        raise ValueError("candidate WAV must be 16-bit")
    if channels != 1:
        raise ValueError("candidate WAV must be mono")
    if compression != "NONE":
        raise ValueError("candidate WAV must contain uncompressed PCM")
    if frame_count != 12 * sample_rate:
        raise ValueError("candidate WAV must be exactly 12.0 seconds")
    return {
        "sample_rate": sample_rate,
        "sample_width": sample_width,
        "channels": channels,
        "frame_count": frame_count,
        "duration_seconds": frame_count / sample_rate,
        "compression": compression,
    }


def validate_candidate(path: str | Path) -> dict[str, int | float | str]:
    audio_path = Path(path)
    if not audio_path.is_file():
        raise ValueError(f"candidate WAV does not exist: {audio_path}")
    return validate_candidate_bytes(audio_path.read_bytes())


def params_with_voice(default_params_json: str | None, voice_id: str) -> str:
    try:
        params = json.loads(default_params_json or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("profile default_params_json is invalid JSON") from exc
    if not isinstance(params, dict):
        raise ValueError("profile default_params_json must contain a JSON object")
    params["voice"] = voice_id
    return json.dumps(params, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def backup_payload(profile: ProfileSnapshot) -> dict[str, object]:
    return {
        "profile_id": profile.profile_id,
        "name": profile.profile_name,
        "default_params_json": profile.default_params_json,
        "ref_audio_path": profile.ref_audio_path,
        "ref_text": profile.ref_text,
    }


def _readonly_connection(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ValueError(f"database does not exist: {path}")
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def load_profile(database_path: str | Path, profile_id: int = PROFILE_ID) -> ProfileSnapshot:
    database = Path(database_path)
    connection = _readonly_connection(database)
    try:
        row = connection.execute(
            "SELECT id, name, default_params_json, ref_audio_path, ref_text "
            "FROM profiles WHERE id = ?",
            (profile_id,),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise ValueError(f"voice profile {profile_id} was not found")
    profile = ProfileSnapshot(
        profile_id=row[0],
        profile_name=row[1],
        default_params_json=row[2],
        ref_audio_path=row[3],
        ref_text=row[4],
    )
    # Validate before any apply-side effect or cloud request.
    params_with_voice(profile.default_params_json, "validation-placeholder")
    return profile


def _default_backup_path(database_path: Path, profile_id: int) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return database_path.parent / "backups" / f"profile_{profile_id}_before_custom_voice_{timestamp}.json"


def prepare_registration(
    *,
    database_path: str | Path,
    audio_path: str | Path,
    transcript_path: str | Path,
    profile_id: int = PROFILE_ID,
    backup_path: str | Path | None = None,
) -> RegistrationPreparation:
    database = Path(database_path).expanduser().resolve()
    audio = Path(audio_path).expanduser().resolve()
    transcript_file = Path(transcript_path).expanduser().resolve()
    profile = load_profile(database, profile_id)
    if not audio.is_file():
        raise ValueError(f"candidate WAV does not exist: {audio}")
    audio_bytes = audio.read_bytes()
    details = validate_candidate_bytes(audio_bytes)
    audio_sha256 = hashlib.sha256(audio_bytes).hexdigest()
    transcript = load_transcript(transcript_file)
    backup = (
        Path(backup_path).expanduser().resolve()
        if backup_path is not None
        else _default_backup_path(database, profile_id)
    )
    return RegistrationPreparation(
        database_path=database,
        audio_path=audio,
        transcript_path=transcript_file,
        backup_path=backup,
        profile=profile,
        ref_text=transcript,
        audio_bytes=audio_bytes,
        audio_sha256=audio_sha256,
        audio_details=details,
    )


def write_backup(preparation: RegistrationPreparation) -> None:
    preparation.backup_path.parent.mkdir(parents=True, exist_ok=True)
    with preparation.backup_path.open("x", encoding="utf-8", newline="\n") as backup_file:
        json.dump(
            backup_payload(preparation.profile),
            backup_file,
            ensure_ascii=False,
            indent=2,
        )
        backup_file.write("\n")


def update_profile(preparation: RegistrationPreparation, voice_id: str) -> None:
    updated_params = params_with_voice(
        preparation.profile.default_params_json,
        voice_id,
    )
    connection = sqlite3.connect(preparation.database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        current = connection.execute(
            "SELECT default_params_json, ref_audio_path, ref_text FROM profiles WHERE id = ?",
            (preparation.profile.profile_id,),
        ).fetchone()
        expected = (
            preparation.profile.default_params_json,
            preparation.profile.ref_audio_path,
            preparation.profile.ref_text,
        )
        if current != expected:
            raise RuntimeError("profile changed after dry-run preparation; refusing update")
        connection.execute(
            "UPDATE profiles SET default_params_json = ?, ref_audio_path = ?, ref_text = ? "
            "WHERE id = ?",
            (
                updated_params,
                str(preparation.audio_path),
                preparation.ref_text,
                preparation.profile.profile_id,
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def ensure_candidate_unchanged(preparation: RegistrationPreparation) -> None:
    try:
        current_bytes = preparation.audio_path.read_bytes()
    except OSError:
        raise RuntimeError(
            "approved candidate changed or became unavailable after preparation"
        ) from None
    current_sha256 = hashlib.sha256(current_bytes).hexdigest()
    if current_sha256 != preparation.audio_sha256:
        raise RuntimeError("approved candidate changed after preparation")


def validate_expected_sha256(
    expected_sha256: str | None,
    actual_sha256: str,
    *,
    required: bool,
) -> str | None:
    if expected_sha256 is None or not expected_sha256.strip():
        if required:
            raise ValueError("--expected-sha256 is required with --apply")
        return None
    value = expected_sha256.strip()
    if not SHA256_PATTERN.fullmatch(value):
        raise ValueError("--expected-sha256 must be exactly 64-hex characters")
    normalized = value.lower()
    if not hmac.compare_digest(normalized, actual_sha256.lower()):
        raise ValueError("--expected-sha256 does not match the prepared candidate")
    return normalized


async def apply_registration(
    preparation: RegistrationPreparation,
    *,
    api_base: str,
    api_key: str,
    title: str,
    expected_sha256: str,
    client=None,
) -> str:
    if not api_key.strip():
        raise ValueError("BOSON_API_KEY is required with --apply")
    validate_expected_sha256(
        expected_sha256,
        preparation.audio_sha256,
        required=True,
    )
    ensure_candidate_unchanged(preparation)
    write_backup(preparation)
    if client is None:
        timeout = httpx.Timeout(connect=10.0, write=30.0, read=180.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as owned_client:
            voice_id = await create_custom_voice(
                owned_client,
                api_base,
                api_key,
                str(preparation.audio_path),
                preparation.ref_text,
                title,
                audio_bytes=preparation.audio_bytes,
            )
    else:
        voice_id = await create_custom_voice(
            client,
            api_base,
            api_key,
            str(preparation.audio_path),
            preparation.ref_text,
            title,
            audio_bytes=preparation.audio_bytes,
        )
    ensure_candidate_unchanged(preparation)
    update_profile(preparation, voice_id)
    return voice_id


def print_dry_run(preparation: RegistrationPreparation) -> None:
    details = preparation.audio_details
    print("DRY RUN ONLY: no cloud request, backup, or database write was performed.")
    print(f"profile: {preparation.profile.profile_id} ({preparation.profile.profile_name})")
    print(f"database: {preparation.database_path}")
    print(f"candidate: {preparation.audio_path}")
    print(f"candidate_sha256: {preparation.audio_sha256}")
    print(
        "candidate_format: "
        f"{details['sample_rate']} Hz, {int(details['sample_width']) * 8}-bit, "
        f"{details['channels']} channel, {details['duration_seconds']:.6f} s"
    )
    print(f"transcript_file: {preparation.transcript_path}")
    print(f"transcript_characters: {len(preparation.ref_text)}")
    print(f"apply_backup: {preparation.backup_path}")
    print("rerun with --apply only after the clip and verbatim transcript are approved")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transcript", required=True, type=Path)
    parser.add_argument("--audio", type=Path, default=DEFAULT_AUDIO)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--backup", type=Path)
    parser.add_argument(
        "--expected-sha256",
        help="approved candidate SHA-256 printed by dry-run; required with --apply",
    )
    parser.add_argument("--api-base", default=API_BASE)
    parser.add_argument("--title", default="月代雪")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="create the Boson voice, back up profile 6, and update the database",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        preparation = prepare_registration(
            database_path=args.database,
            audio_path=args.audio,
            transcript_path=args.transcript,
            backup_path=args.backup,
        )
        expected_sha256 = validate_expected_sha256(
            args.expected_sha256,
            preparation.audio_sha256,
            required=args.apply,
        )
        if not args.apply:
            print_dry_run(preparation)
            return 0
        voice_id = asyncio.run(
            apply_registration(
                preparation,
                api_base=args.api_base,
                api_key=os.environ.get("BOSON_API_KEY", ""),
                title=args.title,
                expected_sha256=expected_sha256,
            )
        )
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"created voice: {mask_voice_id(voice_id)}")
    print(f"backup: {preparation.backup_path}")
    print(f"updated profile: {preparation.profile.profile_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
