import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.config import settings
from app.providers.base import ProviderRequest
from app.providers.piper import PiperProvider


class PiperPublicSafetyTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def request(model_path: Path, timeout: object = 30) -> ProviderRequest:
        return ProviderRequest(
            text="private sentence",
            model_properties={"api_base": "piper", "model_path": str(model_path)},
            profile_config=None,
            params={"timeout": timeout},
            return_format="wav",
        )

    async def test_rejects_output_in_sibling_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "audio"
            audio.mkdir()
            model = root / "voice.onnx"
            model.write_bytes(b"model")
            sibling = root / "audio-private" / "result.wav"
            sibling.parent.mkdir()

            with patch.object(settings, "audio_dir_path", audio):
                with self.assertRaisesRegex(ValueError, "authorized directory"):
                    await PiperProvider().generate(self.request(model), str(sibling))

    async def test_metadata_does_not_expose_executable_or_model_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "audio"
            audio.mkdir()
            output = audio / "result.wav"
            output.write_bytes(b"RIFF")
            model = root / "voice.onnx"
            model.write_bytes(b"model")
            process = MagicMock()
            process.communicate.return_value = ("ok", "")
            process.returncode = 0

            with patch.object(settings, "audio_dir_path", audio), patch(
                "app.providers.piper.subprocess.Popen", return_value=process
            ) as popen:
                result = await PiperProvider().generate(
                    self.request(model, 999999), str(output)
                )

            self.assertEqual(popen.return_value.communicate.call_args.kwargs["timeout"], 120.0)
            self.assertEqual(result.metadata, {"provider": "piper", "speed": None})
            self.assertNotIn(str(root), repr(result.metadata))
            self.assertNotIn("private sentence", repr(result.metadata))


if __name__ == "__main__":
    unittest.main()
