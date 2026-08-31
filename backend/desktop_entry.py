import sys
import os
import argparse
from pathlib import Path
import multiprocessing

# 1. Parse arguments BEFORE importing app modules to override env settings
parser = argparse.ArgumentParser(description="TTS WebUI Workbench Desktop Backend Entry")
parser.add_argument("--host", default="127.0.0.1", help="Host address to bind to")
parser.add_argument("--port", type=int, default=8765, help="Port to listen on")
parser.add_argument("--data-dir", default=None, help="User-writable data directory")
args, unknown = parser.parse_known_args()

# Setup paths and environment variables
if args.data_dir:
    data_path = Path(args.data_dir).resolve()
    db_dir = data_path / "db"
    audio_dir = data_path / "audio"
    ref_dir = data_path / "reference"
    
    db_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)
    ref_dir.mkdir(parents=True, exist_ok=True)
    
    os.environ["DATABASE_URL"] = f"sqlite:///{db_dir}/tts_workbench.db"
    os.environ["AUDIO_DIR_PATH"] = str(audio_dir)
    os.environ["REFERENCE_DIR_PATH"] = str(ref_dir)
    
    # Load .env from data directory if it exists
    env_in_data = data_path / ".env"
    if env_in_data.exists():
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_in_data)

os.environ["PORT"] = str(args.port)
os.environ["HOST"] = args.host

# Import settings and fastapi app after patching environment
from app.main import app
import uvicorn

if __name__ == "__main__":
    multiprocessing.freeze_support()
    print(f"Starting desktop backend server on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, reload=False, workers=1)
