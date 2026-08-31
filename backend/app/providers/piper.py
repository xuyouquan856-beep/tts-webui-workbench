import subprocess
from pathlib import Path

from app.providers.base import BaseTTSProvider, ProviderRequest, ProviderResult
from app.config import settings


MAX_PIPER_TIMEOUT_SECONDS = 120.0


class PiperProvider(BaseTTSProvider):
    async def generate(self, request: ProviderRequest, output_path: str) -> ProviderResult:
        # Validate output path
        resolved_output = Path(output_path).resolve()
        resolved_audio_dir = Path(settings.audio_dir_path).resolve()
        if not resolved_output.is_relative_to(resolved_audio_dir):
            raise ValueError(
                "Security validation failed: output path must reside within its authorized directory."
            )
            
        # Piper executable name/path: defaults to "piper" (in PATH)
        # Can be overridden by the api_base configuration or model_path
        piper_exe = request.model_properties.get("api_base") or "piper"
        
        # ONNX Model path
        model_path = request.model_properties.get("model_path")
        if not model_path or not Path(model_path).is_file():
            raise ValueError(
                "Piper ONNX model path is invalid or the file does not exist."
            )
            
        # Build command arguments
        cmd_args = [
            piper_exe,
            "--model", model_path,
            "--output_file", output_path
        ]
        
        # Add speed (length scale) parameter if provided
        # Piper's default length_scale is 1.0 (larger means slower)
        speed = request.params.get("speed")
        if speed is not None:
            try:
                # convert speed (where e.g. 1.0 is normal, 1.2 is faster)
                # Piper uses length_scale (where 1.0 is normal, 0.8 is faster)
                # length_scale = 1.0 / speed
                speed_val = float(speed)
                if speed_val > 0:
                    length_scale = 1.0 / speed_val
                    cmd_args.extend(["--length_scale", f"{length_scale:.2f}"])
            except (TypeError, ValueError):
                pass
                
        # Capture timeout
        timeout = request.params.get("timeout") or 30.0
        try:
            timeout = float(timeout)
        except (TypeError, ValueError):
            timeout = 30.0
        timeout = min(max(timeout, 1.0), MAX_PIPER_TIMEOUT_SECONDS)
            
        try:
            # Execute Piper and stream text via stdin
            process = subprocess.Popen(
                cmd_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False
            )
            
            # Send the text to Piper's stdin and wait for completion
            stdout, stderr = process.communicate(input=request.text, timeout=timeout)
            
        except FileNotFoundError:
            raise FileNotFoundError(
                "Piper executable was not found. Check the configured executable or PATH."
            ) from None
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.communicate()
            raise TimeoutError(
                f"Piper execution timed out after {timeout:g} seconds."
            ) from exc
        except OSError as exc:
            raise RuntimeError("Piper could not be started.") from exc
            
        if process.returncode != 0:
            raise RuntimeError(
                f"Piper TTS engine failed with return code {process.returncode}."
            )
            
        if not Path(output_path).is_file():
            raise FileNotFoundError(
                "Piper completed successfully without creating an output file."
            )
            
        return ProviderResult(
            audio_path=output_path,
            format="wav",
            metadata={
                "provider": "piper",
                "speed": speed
            }
        )
