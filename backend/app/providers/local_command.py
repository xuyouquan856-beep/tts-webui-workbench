import shlex
import subprocess
from pathlib import Path

from app.providers.base import BaseTTSProvider, ProviderRequest, ProviderResult
from app.config import settings


MAX_COMMAND_TIMEOUT_SECONDS = 120.0


def redact_command(args: list[str]) -> str:
    """Describe a command without exposing arguments, text, or local paths."""

    executable = Path(args[0]).name if args else "command"
    return f"{executable} …"


def _resolve_within(path: str | Path, root: str | Path, label: str) -> Path:
    resolved_path = Path(path).resolve()
    resolved_root = Path(root).resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise ValueError(f"Security validation failed: {label} must reside within its authorized directory.")
    return resolved_path


class LocalCommandProvider(BaseTTSProvider):
    async def generate(self, request: ProviderRequest, output_path: str) -> ProviderResult:
        # 1. Strict path security checks
        _resolve_within(output_path, settings.audio_dir_path, "output path")
            
        # Resolve voice profile paths
        ref_audio_path = None
        ref_text = None
        if request.profile_config:
            ref_audio_path = request.profile_config.get("ref_audio_path")
            ref_text = request.profile_config.get("ref_text")
            
        if ref_audio_path:
            # Check if reference audio is local (not a web URL)
            if not (ref_audio_path.startswith("http://") or ref_audio_path.startswith("https://")):
                _resolve_within(
                    ref_audio_path,
                    settings.reference_dir_path,
                    "reference audio path",
                )
                    
        # 2. Get command template and model path
        command_template = request.model_properties.get("command_template")
        if not command_template:
            raise ValueError("Model configuration is missing a 'command_template'.")
            
        model_path = request.model_properties.get("model_path") or ""
        
        # 3. Perform string replacements for placeholders
        replacements = {
            "{text}": request.text,
            "{output_path}": output_path,
            "{model_path}": model_path,
            "{ref_audio_path}": ref_audio_path or "",
            "{ref_text}": ref_text or ""
        }
        
        populated_cmd = command_template
        for placeholder, value in replacements.items():
            populated_cmd = populated_cmd.replace(placeholder, value)
            
        # 4. Parse arguments safely using shlex (to prevent shell injection)
        try:
            cmd_args = shlex.split(populated_cmd)
        except (TypeError, ValueError) as exc:
            raise ValueError("Failed to parse command template.") from exc
            
        if not cmd_args:
            raise ValueError("Command resolved to an empty argument list.")
            
        # 5. Extract timeout with fallback
        timeout = request.params.get("timeout") or request.model_properties.get("timeout") or 30.0
        try:
            timeout = float(timeout)
        except (TypeError, ValueError):
            timeout = 30.0
        timeout = min(max(timeout, 1.0), MAX_COMMAND_TIMEOUT_SECONDS)
            
        # 6. Execute subprocess securely with shell=False
        try:
            # Note: We run run() in a blocking way, but since it is inside a worker thread,
            # it will not block FastAPI's main event loop (the generation service runs it in a threadpool)
            result = subprocess.run(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
                timeout=timeout
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"TTS command execution timed out after {timeout:g} seconds."
            ) from exc
        except OSError as exc:
            raise RuntimeError("TTS command could not be started.") from exc
            
        # 7. Check execution result
        if result.returncode != 0:
            raise RuntimeError(
                f"TTS command failed with return code {result.returncode}."
            )
            
        # 8. Assert output file was generated
        if not Path(output_path).is_file():
            raise FileNotFoundError(
                "TTS command completed without creating an output file."
            )
            
        return ProviderResult(
            audio_path=output_path,
            format=request.return_format,
            metadata={
                "provider": "local_command",
                "command": redact_command(cmd_args),
                "returncode": result.returncode,
            }
        )
