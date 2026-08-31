import json
import os
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from app.models import ModelConfig, VoiceProfile
from app.providers.base import ProviderRequest, ProviderResult, BaseTTSProvider
from app.providers.dummy import DummyProvider
from app.providers.higgs_api import HiggsApiProvider
from app.providers.local_http import LocalHttpProvider
from app.providers.local_command import LocalCommandProvider
from app.providers.piper import PiperProvider
from app.services.storage import StorageService
from app.services.audio_utils import get_audio_duration

class GenerationService:
    @staticmethod
    def get_provider(provider_type: str) -> BaseTTSProvider:
        """
        Factory method to get the correct provider instance.
        """
        providers = {
            "dummy": DummyProvider,
            "higgs_api": HiggsApiProvider,
            "local_http": LocalHttpProvider,
            "local_command": LocalCommandProvider,
            "piper": PiperProvider
        }
        
        provider_cls = providers.get(provider_type.lower())
        if not provider_cls:
            raise ValueError(f"Unknown or unsupported TTS Provider type: '{provider_type}'")
        return provider_cls()

    @staticmethod
    async def generate_audio(
        db: Session,
        job_id: str,
        text: str,
        model_id: int,
        profile_id: Optional[int],
        params_json: str,
        return_format: str
    ) -> ProviderResult:
        """
        Asynchronously generates audio, coordinating models, profiles, and providers.
        """
        req = GenerationService.resolve_provider_request(
            db=db,
            text=text,
            model_id=model_id,
            profile_id=profile_id,
            params_json=params_json,
            return_format=return_format,
        )

        # Determine output file path
        output_path = StorageService.get_audio_output_path(job_id, req.return_format)

        # Get provider instance and generate
        provider = GenerationService.get_provider(req.model_properties["provider_type"])
        result = await provider.generate(req, output_path)

        # Calculate duration if it's not set
        if not result.duration:
            result.duration = get_audio_duration(output_path)

        return result

    @staticmethod
    def resolve_provider_request(
        db: Session,
        text: str,
        model_id: int,
        profile_id: Optional[int],
        params_json: str,
        return_format: str,
    ) -> ProviderRequest:
        """Build the provider request shared by blocking and streaming synthesis."""
        # 1. Retrieve model configuration
        model = db.query(ModelConfig).filter(ModelConfig.id == model_id).first()
        if not model:
            raise ValueError(f"ModelConfig with ID {model_id} not found.")
        if not model.enabled:
            raise ValueError(f"ModelConfig '{model.name}' is currently disabled.")
            
        # 2. Retrieve voice profile if specified
        profile_data = None
        if profile_id:
            profile = db.query(VoiceProfile).filter(VoiceProfile.id == profile_id).first()
            if not profile:
                raise ValueError(f"VoiceProfile with ID {profile_id} not found.")
            profile_data = {
                "id": profile.id,
                "name": profile.name,
                "language": profile.language,
                "provider_type": profile.provider_type,
                "ref_audio_path": profile.ref_audio_path,
                "ref_text": profile.ref_text,
                "default_params": json.loads(profile.default_params_json or "{}")
            }
            
        # 3. Assemble parameters
        # Merge hierarchy: ModelConfig params_json -> VoiceProfile default_params -> request parameters
        model_params = json.loads(model.params_json or "{}")
        profile_params = profile_data["default_params"] if profile_data else {}
        request_params = json.loads(params_json or "{}")
        
        merged_params = {}
        merged_params.update(model_params)
        merged_params.update(profile_params)
        merged_params.update(request_params)
        
        # 4. Set up provider request
        model_config_dict = {
            "id": model.id,
            "name": model.name,
            "provider_type": model.provider_type,
            "api_base": model.api_base,
            "model_name": model.model_name,
            "command_template": model.command_template,
            "model_path": model.model_path,
            "output_format": model.output_format,
            "params": model_params
        }
        
        req = ProviderRequest(
            text=text,
            model_properties=model_config_dict,
            profile_config=profile_data,
            params=merged_params,
            return_format=return_format or model.output_format or "wav"
        )
        
        return req
