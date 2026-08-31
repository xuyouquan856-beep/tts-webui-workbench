import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class ModelConfig(Base):
    __tablename__ = "models"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    provider_type = Column(String, nullable=False)  # dummy, higgs_api, local_http, local_command, piper
    api_base = Column(String, nullable=True)
    model_name = Column(String, nullable=True)
    command_template = Column(String, nullable=True)
    model_path = Column(String, nullable=True)
    output_format = Column(String, default="wav")
    enabled = Column(Boolean, default=True)
    params_json = Column(String, default="{}")  # Fallback/default params as JSON string
    
    profiles = relationship("VoiceProfile", back_populates="model")


class VoiceProfile(Base):
    __tablename__ = "profiles"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    language = Column(String, default="ja")
    provider_type = Column(String, nullable=False)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=True)
    ref_audio_path = Column(String, nullable=True)  # Path in data/reference/
    ref_text = Column(String, nullable=True)
    default_params_json = Column(String, default="{}")  # Default parameters specific to this voice

    model = relationship("ModelConfig", back_populates="profiles")


class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, index=True)  # UUID string
    text = Column(String, nullable=False)
    model_id = Column(Integer, nullable=False)
    profile_id = Column(Integer, nullable=True)
    status = Column(String, default="queued")  # queued, running, succeeded, failed
    params_json = Column(String, default="{}")
    return_format = Column(String, default="wav")
    audio_path = Column(String, nullable=True)  # Path in data/audio/
    audio_url = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    duration = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
