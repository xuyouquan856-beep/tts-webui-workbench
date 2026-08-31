import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, ModelConfig
from app.schemas import GenerateRequest, JobResponse
from app.queue import job_queue

router = APIRouter(prefix="", tags=["Generation"])

@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_speech(req: GenerateRequest, db: Session = Depends(get_db)):
    """
    Submits a Text-to-Speech generation job. Returns the generated job_id.
    """
    # Verify model exists and is enabled
    model = db.query(ModelConfig).filter(ModelConfig.id == req.model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"ModelConfig with ID {req.model_id} not found"
        )
    if not model.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"ModelConfig '{model.name}' is currently disabled"
        )
        
    # Generate unique Job ID
    job_id = uuid.uuid4().hex
    
    # Store job in database
    db_job = Job(
        id=job_id,
        text=req.text,
        model_id=req.model_id,
        profile_id=req.profile_id,
        status="queued",
        params_json=json.dumps(req.params),
        return_format=req.return_format or model.output_format or "wav"
    )
    db.add(db_job)
    db.commit()
    
    # Enqueue job to background queue
    await job_queue.put(job_id)
    
    return {"job_id": job_id, "status": "queued"}

@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Fetch status of a specific TTS generation job.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    return job
