from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Optional, Dict, Any

class ProviderRequest(BaseModel):
    text: str
    model_properties: Dict[str, Any]  # Key attributes of ModelConfig (renamed from model_config to avoid Pydantic conflict)
    profile_config: Optional[Dict[str, Any]] = None  # Key attributes of VoiceProfile
    params: Dict[str, Any]  # Execution specific params (e.g. speed, pitch, tags, emotion)
    return_format: str      # output format (wav, mp3, etc)

class ProviderResult(BaseModel):
    audio_path: str
    format: str
    metadata: Dict[str, Any] = {}
    duration: Optional[float] = None

class BaseTTSProvider(ABC):
    @abstractmethod
    async def generate(self, request: ProviderRequest, output_path: str) -> ProviderResult:
        """
        Synthesizes text to speech and writes the result to output_path.
        Returns a ProviderResult object.
        """
        pass
