from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import VoiceProfile
from app.schemas import VoiceProfileCreate, VoiceProfileResponse
from app.services.storage import StorageService

router = APIRouter(prefix="/profiles", tags=["Profiles"])

@router.get("", response_model=List[VoiceProfileResponse])
def list_profiles(db: Session = Depends(get_db)):
    """
    List all voice profiles.
    """
    return db.query(VoiceProfile).all()

@router.post("", response_model=VoiceProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(profile_in: VoiceProfileCreate, db: Session = Depends(get_db)):
    """
    Create a new voice profile.
    """
    db_profile = VoiceProfile(
        name=profile_in.name,
        language=profile_in.language,
        provider_type=profile_in.provider_type,
        model_id=profile_in.model_id,
        ref_audio_path=profile_in.ref_audio_path,
        ref_text=profile_in.ref_text,
        default_params_json=profile_in.default_params_json
    )
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile

def handle_upload(profile_id: int, file: UploadFile, db: Session):
    db_profile = db.query(VoiceProfile).filter(VoiceProfile.id == profile_id).first()
    if not db_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VoiceProfile with ID {profile_id} not found"
        )

    try:
        # Read uploaded content
        content = file.file.read()

        # Save audio using storage service
        saved_path = StorageService.save_reference_audio(profile_id, content, file.filename)

        # Update database entry
        db_profile.ref_audio_path = saved_path
        db.commit()
        db.refresh(db_profile)
        return db_profile
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save reference audio file."
        ) from e

@router.post("/{profile_id}/reference-audio", response_model=VoiceProfileResponse)
def upload_reference_audio_v1(profile_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload reference audio file for voice cloning (Endpoint A).
    """
    return handle_upload(profile_id, file, db)

@router.post("/{profile_id}/upload-reference", response_model=VoiceProfileResponse)
def upload_reference_audio_v2(profile_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload reference audio file for voice cloning (Endpoint B).
    """
    return handle_upload(profile_id, file, db)

@router.delete("/{voice_profile_id}")
def delete_voice_profile(voice_profile_id: int, delete_reference_audio: bool = False, db: Session = Depends(get_db)):
    """
    Deletes a specific voice profile.
    Optionally deletes the referenced cloned voice reference audio.
    """
    from pathlib import Path
    from app.config import settings

    def is_safe_path(base_dir: Path, target_path: str) -> bool:
        try:
            resolved_base = base_dir.resolve()
            resolved_target = Path(target_path).resolve()
            return resolved_base in resolved_target.parents
        except Exception:
            return False

    db_profile = db.query(VoiceProfile).filter(VoiceProfile.id == voice_profile_id).first()
    if not db_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到该声音配置 (ID: {voice_profile_id})"
        )

    file_deleted = False
    file_error = None

    if delete_reference_audio and db_profile.ref_audio_path:
        if is_safe_path(settings.reference_dir_path, db_profile.ref_audio_path):
            try:
                p = Path(db_profile.ref_audio_path)
                if p.exists() and p.is_file():
                    p.unlink()
                    file_deleted = True
            except Exception:
                file_error = "参考音频文件删除失败"
        else:
            file_error = "文件路径超出克隆参考音频文件夹安全范围"

    db.delete(db_profile)
    db.commit()

    if file_error:
        return {
            "status": "partial_success",
            "message": f"声音配置已从数据库删除，但克隆参考音频文件删除失败: {file_error}"
        }

    return {
        "status": "success",
        "message": "声音配置已删除"
    }
