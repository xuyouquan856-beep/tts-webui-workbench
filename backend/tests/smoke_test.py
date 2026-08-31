import asyncio
import argparse
import os
import sys
from pathlib import Path

parser = argparse.ArgumentParser(description="Run an isolated Dummy TTS smoke test")
parser.add_argument("--data-dir", help="Use an isolated writable data directory")
args = parser.parse_args()

if args.data_dir:
    data_dir = Path(args.data_dir).resolve()
    db_dir = data_dir / "db"
    audio_dir = data_dir / "audio"
    reference_dir = data_dir / "reference"
    for directory in (db_dir, audio_dir, reference_dir):
        directory.mkdir(parents=True, exist_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite:///{db_dir}/tts_workbench.db"
    os.environ["AUDIO_DIR_PATH"] = str(audio_dir)
    os.environ["REFERENCE_DIR_PATH"] = str(reference_dir)

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.database import engine, Base, SessionLocal
from app.models import ModelConfig, VoiceProfile, Job
from app.services.generation_service import GenerationService
from app.config import settings

async def run_smoke_test():
    print("--- Starting Backend Smoke Test ---")
    
    # 1. Initialize Tables
    print("Initializing SQLite Database Tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 2. Add Dummy Model & Profile if not present
        dummy_model = db.query(ModelConfig).filter(ModelConfig.provider_type == "dummy").first()
        if not dummy_model:
            print("Adding Dummy Model Config...")
            dummy_model = ModelConfig(
                name="Test Dummy Model",
                provider_type="dummy",
                enabled=True,
                output_format="wav",
                params_json="{}"
            )
            db.add(dummy_model)
            db.commit()
            db.refresh(dummy_model)
            
        dummy_profile = db.query(VoiceProfile).filter(VoiceProfile.provider_type == "dummy").first()
        if not dummy_profile:
            print("Adding Dummy Voice Profile...")
            dummy_profile = VoiceProfile(
                name="Test Dummy Voice Profile",
                language="ja",
                provider_type="dummy",
                model_id=dummy_model.id,
                default_params_json="{}"
            )
            db.add(dummy_profile)
            db.commit()
            db.refresh(dummy_profile)
            
        print(f"Using Model ID: {dummy_model.id}, Profile ID: {dummy_profile.id}")
        
        # 3. Trigger TTS Generation via GenerationService
        job_id = "test_smoke_job_id"
        # Ensure target file doesn't exist
        target_path = Path(settings.audio_dir_path) / f"{job_id}.wav"
        if target_path.exists():
            target_path.unlink()
            
        print("Generating TTS beep audio using DummyProvider...")
        result = await GenerationService.generate_audio(
            db=db,
            job_id=job_id,
            text="Hello World. This is a smoke test.",
            model_id=dummy_model.id,
            profile_id=dummy_profile.id,
            params_json="{}",
            return_format="wav"
        )
        
        # 4. Asserts
        print("Verifying outputs...")
        assert os.path.exists(result.audio_path), f"Output file does not exist: {result.audio_path}"
        assert result.format == "wav", f"Format mismatch: expected 'wav', got '{result.format}'"
        assert result.duration == 1.0, f"Duration mismatch: expected 1.0, got {result.duration}"
        
        # Validate wave header
        with open(result.audio_path, 'rb') as f:
            header = f.read(12)
            assert header[0:4] == b'RIFF' and header[8:12] == b'WAVE', "Generated file is not a valid WAVE file."
            
        print("SUCCESS: Audio file successfully generated and verified!")
        
        # Cleanup test files from data/audio
        if target_path.exists():
            target_path.unlink()
            print("Cleanup completed.")
            
    except Exception as e:
        print(f"SMOKE TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_smoke_test())
