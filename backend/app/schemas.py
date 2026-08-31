from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

# --- Model Configurations ---
class ModelConfigBase(BaseModel):
    name: str
    provider_type: str
    api_base: Optional[str] = None
    model_name: Optional[str] = None
    command_template: Optional[str] = None
    model_path: Optional[str] = None
    output_format: str = "wav"
    enabled: bool = True
    params_json: str = "{}"

class ModelConfigCreate(ModelConfigBase):
    pass

class ModelConfigResponse(ModelConfigBase):
    id: int

    class Config:
        from_attributes = True


# --- Voice Profiles ---
class VoiceProfileBase(BaseModel):
    name: str
    language: str = "ja"
    provider_type: str
    model_id: Optional[int] = None
    ref_audio_path: Optional[str] = None
    ref_text: Optional[str] = None
    default_params_json: str = "{}"

class VoiceProfileCreate(VoiceProfileBase):
    pass

class VoiceProfileResponse(VoiceProfileBase):
    id: int

    class Config:
        from_attributes = True


# --- Jobs ---
class GenerateRequest(BaseModel):
    text: str
    model_id: int
    profile_id: Optional[int] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    return_format: str = "wav"

class JobResponse(BaseModel):
    id: str
    text: str
    model_id: int
    profile_id: Optional[int] = None
    status: str
    params_json: str
    return_format: str
    audio_path: Optional[str] = None
    audio_url: Optional[str] = None
    error_message: Optional[str] = None
    duration: Optional[float] = None
    created_at: datetime
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Speak Endpoint ---
class SpeakRequest(BaseModel):
    text: str
    model_id: Optional[int] = None
    profile_id: Optional[int] = None
    params: Dict[str, Any] = Field(default_factory=dict)

class SpeakResponse(BaseModel):
    job_id: str
    status: str
    audio_url: Optional[str] = None
    duration: Optional[float] = None
    error: Optional[str] = None
