import asyncio
import logging
import datetime
import traceback
import os
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Job
from app.services.generation_service import GenerationService

logger = logging.getLogger("queue_worker")
logging.basicConfig(level=logging.INFO)

# Global memory queue
job_queue = asyncio.Queue()

async def queue_worker_loop():
    """
    Main background worker loop. Reads job IDs from the queue and executes them sequentially.
    """
    logger.info("Background queue worker loop started.")
    while True:
        job_id = await job_queue.get()
        logger.info(f"Processing job from queue: {job_id}")
        
        db = SessionLocal()
        try:
            # Fetch job from db
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                logger.warning(f"Job {job_id} not found in database. Skipping.")
                continue
                
            # Update status to running
            job.status = "running"
            db.commit()
            
            # Start timer
            start_time = datetime.datetime.utcnow()
            
            # Run generation service (fully async)
            result = await GenerationService.generate_audio(
                db=db,
                job_id=job.id,
                text=job.text,
                model_id=job.model_id,
                profile_id=job.profile_id,
                params_json=job.params_json,
                return_format=job.return_format
            )
            
            # Calculate duration
            end_time = datetime.datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            # Update job state
            job.status = "succeeded"
            job.audio_path = result.audio_path
            
            # Formulate audio stream url
            filename = os.path.basename(result.audio_path)
            job.audio_url = f"/api/audio/{filename}"
            job.duration = result.duration or duration
            job.finished_at = end_time
            db.commit()
            logger.info(f"Job {job_id} completed successfully in {duration:.2f}s.")
            
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Update job state to failed
            try:
                # Reload job
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = "failed"
                    job.error_message = str(e)
                    job.finished_at = datetime.datetime.utcnow()
                    db.commit()
            except Exception as db_err:
                logger.error(f"Failed to record job failure in database: {str(db_err)}")
                
        finally:
            db.close()
            job_queue.task_done()
