import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ModelConfig, VoiceProfile
from app.schemas import SpeakRequest
from app.services.generation_service import GenerationService


router = APIRouter(prefix="/speak", tags=["Desktop Pet Speak"])

PCM_HEADERS = {
    "X-Audio-Sample-Rate": "24000",
    "X-Audio-Channels": "1",
    "X-Audio-Sample-Format": "s16le",
}


def _resolve_model_id(
    db: Session, model_id: int | None, profile_id: int | None
) -> int:
    if profile_id:
        profile = db.query(VoiceProfile).filter(VoiceProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"VoiceProfile {profile_id} not found",
            )
        if not model_id:
            model_id = profile.model_id

    if not model_id:
        model = db.query(ModelConfig).filter(ModelConfig.enabled == True).first()
        if not model:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No model_id specified, and no enabled default model found in database.",
            )
        model_id = model.id

    return model_id


@router.post("/stream")
async def speak_stream(req: SpeakRequest, db: Session = Depends(get_db)):
    model_id = _resolve_model_id(db, req.model_id, req.profile_id)
    try:
        provider_request = GenerationService.resolve_provider_request(
            db=db,
            text=req.text,
            model_id=model_id,
            profile_id=req.profile_id,
            params_json=json.dumps(req.params),
            return_format="pcm",
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
        ) from error

    if provider_request.model_properties["provider_type"].lower() != "higgs_api":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Streaming PCM is only supported by the higgs_api provider.",
        )

    provider = GenerationService.get_provider("higgs_api")
    upstream_stream = provider.stream_pcm(provider_request)
    try:
        first_chunk = await anext(upstream_stream)
    except ValueError as error:
        await upstream_stream.aclose()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
        ) from error
    except StopAsyncIteration as error:
        await upstream_stream.aclose()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Higgs streaming response was empty.",
        ) from error
    except Exception as error:
        await upstream_stream.aclose()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Higgs streaming request failed.",
        ) from error

    async def pcm_chunks():
        try:
            yield first_chunk
            async for chunk in upstream_stream:
                yield chunk
        finally:
            await upstream_stream.aclose()

    return StreamingResponse(
        pcm_chunks(), media_type="application/octet-stream", headers=PCM_HEADERS
    )
