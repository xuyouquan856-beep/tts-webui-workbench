import uuid
import datetime
import json
import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, ModelConfig, VoiceProfile
from app.schemas import SpeakRequest, SpeakResponse
from app.services.generation_service import GenerationService

router = APIRouter(prefix="/speak", tags=["Desktop Pet Speak"])

@router.post("", response_model=SpeakResponse)
async def speak(req: SpeakRequest, db: Session = Depends(get_db)):
    """
    Synchronous-like TTS generation endpoint for desktop pets.
    Generates audio immediately and returns the audio URL and duration.
    """
    model_id = req.model_id
    profile_id = req.profile_id
    
    # 1. Resolve model and profile
    if profile_id:
        profile = db.query(VoiceProfile).filter(VoiceProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"VoiceProfile {profile_id} not found"
            )
        # Use profile's assigned model if model_id is not explicitly requested
        if not model_id:
            model_id = profile.model_id
            
    if not model_id:
        # If neither is specified, pick the first enabled model (fallback)
        first_enabled = db.query(ModelConfig).filter(ModelConfig.enabled == True).first()
        if not first_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No model_id specified, and no enabled default model found in database."
            )
        model_id = first_enabled.id
        
    model = db.query(ModelConfig).filter(ModelConfig.id == model_id).first()
    if not model or not model.enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ModelConfig with ID {model_id} is missing or disabled."
        )
        
    # Create a job ID
    job_id = uuid.uuid4().hex
    
    # Create Job record in db
    db_job = Job(
        id=job_id,
        text=req.text,
        model_id=model_id,
        profile_id=profile_id,
        status="running",
        params_json=json.dumps(req.params),
        return_format=model.output_format or "wav"
    )
    db.add(db_job)
    db.commit()
    
    # Generate audio immediately (does not go to background loop)
    start_time = datetime.datetime.utcnow()
    try:
        result = await GenerationService.generate_audio(
            db=db,
            job_id=job_id,
            text=req.text,
            model_id=model_id,
            profile_id=profile_id,
            params_json=db_job.params_json,
            return_format=db_job.return_format
        )
        
        # Calculate duration
        end_time = datetime.datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Update job database entry
        db_job.status = "succeeded"
        db_job.audio_path = result.audio_path
        filename = os.path.basename(result.audio_path)
        db_job.audio_url = f"/api/audio/{filename}"
        db_job.duration = result.duration or duration
        db_job.finished_at = end_time
        db.commit()
        
        return SpeakResponse(
            job_id=job_id,
            status="succeeded",
            audio_url=db_job.audio_url,
            duration=db_job.duration
        )
        
    except Exception as e:
        # Mark job as failed in db
        db_job.status = "failed"
        db_job.error_message = str(e)
        db_job.finished_at = datetime.datetime.utcnow()
        db.commit()
        
        return SpeakResponse(
            job_id=job_id,
            status="failed",
            error=str(e)
        )
