import asyncio
import logging
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load env variables from .env if present
load_dotenv()

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models import ModelConfig, VoiceProfile
from app.queue import queue_worker_loop
from app.routers import providers, models, profiles, generate, audio, history, speak, speak_stream, translate
from app.services.http_client import close_http_client, start_http_client
from app.public_policy import (
    APP_VERSION,
    PUBLIC_CORS_ORIGINS,
    build_default_model_specs,
    build_health_payload,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

def seed_database(db):
    """
    Inserts default seed configurations on first boot.
    """
    # 1. Models seeding
    if db.query(ModelConfig).count() == 0:
        logger.info("Database is empty. Seeding default models configurations...")
        
        default_models = [
            ModelConfig(**spec)
            for spec in build_default_model_specs(
                has_boson_key=bool(settings.boson_api_key)
            )
        ]
        
        for m in default_models:
            db.add(m)
        db.commit()
        
        # 2. Profiles seeding
        if db.query(VoiceProfile).count() == 0:
            logger.info("Seeding default voice profiles...")
            # Query models to link correctly
            seeded_models = db.query(ModelConfig).all()
            model_map = {m.provider_type: m.id for m in seeded_models}
            
            default_profiles = [
                VoiceProfile(
                    name="System Beep",
                    language="ja",
                    provider_type="dummy",
                    model_id=model_map.get("dummy"),
                    default_params_json="{}"
                ),
                VoiceProfile(
                    name="Higgs Affinity Female",
                    language="ja",
                    provider_type="higgs_api",
                    model_id=model_map.get("higgs_api"),
                    default_params_json=json.dumps({"voice": "affinity"})
                ),
                VoiceProfile(
                    name="Local HTTP Custom Voice",
                    language="ja",
                    provider_type="local_http",
                    model_id=model_map.get("local_http"),
                    default_params_json="{}"
                ),
                VoiceProfile(
                    name="Piper English Voice",
                    language="en",
                    provider_type="piper",
                    model_id=model_map.get("piper"),
                    default_params_json="{}"
                )
            ]
            for p in default_profiles:
                db.add(p)
            db.commit()
            logger.info("Seed data successfully completed.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Starting up database and tables...")
    Base.metadata.create_all(bind=engine)
    
    # Run seed script
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

    await start_http_client()
    worker_task = None
    try:
        # Start the sequential background queue worker task
        worker_task = asyncio.create_task(queue_worker_loop())
        yield
    finally:
        try:
            # Shutdown actions
            if worker_task is not None:
                logger.info("Shutting down background queue worker task...")
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass
        finally:
            await close_http_client()

# Initialize FastAPI
app = FastAPI(
    title="TTS WebUI Workbench API",
    description="Unified API interface for multiple cloud and local TTS providers",
    version=APP_VERSION,
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=PUBLIC_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup sub-router structure
api_router = APIRouter(prefix="/api")
api_router.include_router(providers.router)
api_router.include_router(models.router)
api_router.include_router(profiles.router)
api_router.include_router(generate.router)
api_router.include_router(audio.router)
api_router.include_router(history.router)
api_router.include_router(speak.router)
api_router.include_router(speak_stream.router)
api_router.include_router(translate.router)

# Healthcheck route
@api_router.get("/health", tags=["Health"])
def health_check():
    return build_health_payload(has_boson_key=bool(settings.boson_api_key))

# Mount all API endpoints under /api
app.include_router(api_router)
