import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Absolute paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DB_DIR = DATA_DIR / "db"
AUDIO_DIR = DATA_DIR / "audio"
REFERENCE_DIR = DATA_DIR / "reference"

# Ensure directories exist
DB_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8000
    
    # SQLite
    database_url: str = f"sqlite:///{DB_DIR}/tts_workbench.db"
    
    # API key (must be configured in environment or .env)
    boson_api_key: str = ""

    # Translation settings
    translation_provider: str = "openai_compatible"
    translation_api_base: str = ""
    translation_api_key: str = ""
    translation_model: str = ""
    
    # Paths for access validation
    audio_dir_path: Path = AUDIO_DIR
    reference_dir_path: Path = REFERENCE_DIR
    
    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = 'utf-8'
        extra = "ignore"

# Instantiate settings
settings = Settings()

# Post-process environment variable fallback directly if pydantic-settings misses it
if not settings.boson_api_key:
    settings.boson_api_key = os.getenv("BOSON_API_KEY", "")

if not settings.translation_provider:
    settings.translation_provider = os.getenv("TRANSLATION_PROVIDER", "openai_compatible")
if not settings.translation_api_base:
    settings.translation_api_base = os.getenv("TRANSLATION_API_BASE", "")
if not settings.translation_api_key:
    settings.translation_api_key = os.getenv("TRANSLATION_API_KEY", "")
if not settings.translation_model:
    settings.translation_model = os.getenv("TRANSLATION_MODEL", "gpt-3.5-turbo")
