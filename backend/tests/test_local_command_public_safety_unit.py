import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.providers import local_command
from app.providers.base import ProviderRequest
from app.providers.local_command import LocalCommandProvider


class LocalCommandPublicSafetyTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def request(text: str, timeout: object = 30) -> ProviderRequest:
        return ProviderRequest(
            text=text,
            model_properties={
                "command_template": (
                    'python synth.py --text "{text}" --out "{output_path}"'
                )
            },
            profile_config=None,
            params={"timeout": timeout},
            return_format="wav",
        )

    async def test_metadata_does_not_echo_text_or_private_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "audio" / "result.wav"
            output.parent.mkdir()
            output.write_bytes(b"RIFF")
            completed = subprocess.CompletedProcess(["python"], 0, "ok", "")

            with patch.object(
                local_command.settings, "audio_dir_path", output.parent
            ), patch.object(local_command.subprocess, "run", return_value=completed):
                result = await LocalCommandProvider().generate(
                    self.request("secret sentence"), str(output)
                )

            self.assertEqual(result.metadata["command"], "python …")
            self.assertNotIn("secret sentence", repr(result.metadata))
            self.assertNotIn(str(root), repr(result.metadata))

    async def test_timeout_is_clamped_to_120_seconds(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.wav"
            with patch.object(
                local_command.settings, "audio_dir_path", output.parent
            ), patch.object(
                local_command.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired("python", 120),
            ) as run:
                with self.assertRaisesRegex(TimeoutError, "120") as raised:
                    await LocalCommandProvider().generate(
                        self.request("private phrase", 999999), str(output)
                    )

            self.assertEqual(run.call_args.kwargs["timeout"], 120.0)
            self.assertNotIn("private phrase", str(raised.exception))
            self.assertNotIn(str(output), str(raised.exception))

    async def test_sibling_directory_does_not_pass_containment_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "audio"
            audio.mkdir()
            sibling = root / "audio-private" / "result.wav"
            sibling.parent.mkdir()

            with patch.object(local_command.settings, "audio_dir_path", audio):
                with self.assertRaisesRegex(ValueError, "authorized directory"):
                    await LocalCommandProvider().generate(
                        self.request("hello"), str(sibling)
                    )


if __name__ == "__main__":
    unittest.main()
