import os
import shutil
from pathlib import Path
from app.config import settings

class StorageService:
    @staticmethod
    def get_audio_output_path(job_id: str, extension: str = "wav") -> str:
        """
        Generates the absolute path where the generated audio file for a job should be stored.
        """
        # Strip leading dots or slashes from extension to prevent traversal
        ext = extension.lstrip(".")
        filename = f"{job_id}.{ext}"
        return str(settings.audio_dir_path / filename)

    @staticmethod
    def save_reference_audio(profile_id: int, file_content: bytes, original_filename: str) -> str:
        """
        Saves uploaded reference audio file to data/reference/ and returns its absolute path.
        """
        # Standardize naming to prevent directory traversal
        _, ext = os.path.splitext(original_filename)
        if not ext:
            ext = ".wav"
        filename = f"profile_{profile_id}{ext}"
        target_path = settings.reference_dir_path / filename
        
        with open(target_path, "wb") as f:
            f.write(file_content)
            
        return str(target_path)
