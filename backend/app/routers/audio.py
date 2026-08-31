import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.models import Job

router = APIRouter(prefix="/audio", tags=["Audio"])


def _managed_audio_file(path: str | Path) -> Path | None:
    candidate = Path(path).resolve()
    audio_root = Path(settings.audio_dir_path).resolve()
    if candidate.is_relative_to(audio_root) and candidate.is_file():
        return candidate
    return None

@router.get("/{identifier}")
def get_audio_file(identifier: str, db: Session = Depends(get_db)):
    """
    Serves a generated audio file.
    Accepts either the literal filename (e.g., 'abc.wav') or the Job ID.
    """
    # 1. Try resolving as direct filename inside data/audio/
    # Sanitize path to prevent directory traversal
    filename = os.path.basename(identifier)
    file_path = settings.audio_dir_path / filename
    
    managed_file = _managed_audio_file(file_path)
    if managed_file:
        return FileResponse(managed_file)
        
    # 2. Try resolving as a Job ID
    job = db.query(Job).filter(Job.id == identifier).first()
    if job and job.audio_path:
        managed_file = _managed_audio_file(job.audio_path)
        if managed_file:
            return FileResponse(managed_file)
        
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Audio file or job reference '{identifier}' could not be found."
    )
