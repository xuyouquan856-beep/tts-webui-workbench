from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.services.translation_service import get_translation_provider

router = APIRouter(prefix="/translate", tags=["Translation"])

class TranslateRequest(BaseModel):
    text: str
    style: str

class TranslateResponse(BaseModel):
    original_text: str
    translated_text: str
    target_language: str = "ja"
    style: str

@router.post("/japanese", response_model=TranslateResponse)
async def translate_japanese(req: TranslateRequest):
    """
    Translates input text into natural Japanese before TTS voice synthesis.
    """
    try:
        provider = get_translation_provider()
        translated = await provider.translate(req.text, req.style)
        return TranslateResponse(
            original_text=req.text,
            translated_text=translated,
            target_language="ja",
            style=req.style
        )
    except ValueError as val_err:
        # Configuration issues
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as e:
        # General runtime translation issues
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
