from fastapi import APIRouter, Depends
from typing import List

router = APIRouter(prefix="/providers", tags=["Providers"])

@router.get("", response_model=List[str])
def get_providers():
    """
    Returns the supported TTS Provider list.
    """
    return ["dummy", "higgs_api", "local_http", "local_command", "piper"]
