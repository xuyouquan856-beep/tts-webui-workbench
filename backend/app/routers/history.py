from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Job
from app.schemas import JobResponse

router = APIRouter(prefix="/history", tags=["History"])

from fastapi import HTTPException, status
from pathlib import Path
from app.config import settings

def is_safe_path(base_dir: Path, target_path: str) -> bool:
    try:
        resolved_base = base_dir.resolve()
        resolved_target = Path(target_path).resolve()
        return resolved_base in resolved_target.parents
    except Exception:
        return False

@router.get("", response_model=List[JobResponse])
def get_history(db: Session = Depends(get_db)):
    """
    Returns all generation jobs, sorted by created_at descending.
    """
    return db.query(Job).order_by(Job.created_at.desc()).all()

@router.delete("/{job_id}")
def delete_history_item(job_id: str, delete_audio_files: bool = False, db: Session = Depends(get_db)):
    """
    Deletes a specific job record from the database.
    Optionally deletes the generated audio file if resides in audio dir.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到该历史记录 (ID: {job_id})"
        )

    file_deleted = False
    file_error = None

    if delete_audio_files and job.audio_path:
        if is_safe_path(settings.audio_dir_path, job.audio_path):
            try:
                p = Path(job.audio_path)
                if p.exists() and p.is_file():
                    p.unlink()
                    file_deleted = True
            except Exception:
                file_error = "音频文件删除失败"
        else:
            file_error = "文件路径超出系统音频文件夹安全范围"

    db.delete(job)
    db.commit()

    if file_error:
        return {
            "status": "partial_success",
            "message": f"历史记录已从数据库删除，但音频文件删除失败: {file_error}"
        }

    return {
        "status": "success",
        "message": "历史记录已删除"
    }

@router.delete("")
def clear_history(delete_audio_files: bool = False, db: Session = Depends(get_db)):
    """
    Clears all job records from the database.
    Optionally deletes all associated audio files.
    """
    jobs = db.query(Job).all()
    deleted_records_count = len(jobs)
    deleted_files_count = 0
    failed_files_count = 0

    for job in jobs:
        if delete_audio_files and job.audio_path:
            if is_safe_path(settings.audio_dir_path, job.audio_path):
                try:
                    p = Path(job.audio_path)
                    if p.exists() and p.is_file():
                        p.unlink()
                        deleted_files_count += 1
                except Exception:
                    failed_files_count += 1
            else:
                failed_files_count += 1
        db.delete(job)

    db.commit()

    status_str = "success" if failed_files_count == 0 else "partial_success"
    msg = "历史记录已清空" if failed_files_count == 0 else f"历史记录已从数据库清空，但有 {failed_files_count} 个音频文件删除失败。"

    return {
        "status": status_str,
        "deleted_records_count": deleted_records_count,
        "deleted_files_count": deleted_files_count,
        "failed_files_count": failed_files_count,
        "message": msg
    }
