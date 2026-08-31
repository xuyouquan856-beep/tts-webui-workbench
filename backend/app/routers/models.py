from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import ModelConfig
from app.schemas import ModelConfigCreate, ModelConfigResponse

router = APIRouter(prefix="/models", tags=["Models"])

@router.get("", response_model=List[ModelConfigResponse])
def list_models(db: Session = Depends(get_db)):
    """
    List all model configurations.
    """
    return db.query(ModelConfig).all()

@router.post("", response_model=ModelConfigResponse, status_code=status.HTTP_201_CREATED)
def create_model(model_in: ModelConfigCreate, db: Session = Depends(get_db)):
    """
    Create a new model configuration.
    """
    db_model = ModelConfig(
        name=model_in.name,
        provider_type=model_in.provider_type,
        api_base=model_in.api_base,
        model_name=model_in.model_name,
        command_template=model_in.command_template,
        model_path=model_in.model_path,
        output_format=model_in.output_format,
        enabled=model_in.enabled,
        params_json=model_in.params_json
    )
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model

@router.put("/{model_id}", response_model=ModelConfigResponse)
def update_model(model_id: int, model_in: ModelConfigCreate, db: Session = Depends(get_db)):
    """
    Update an existing model configuration.
    """
    db_model = db.query(ModelConfig).filter(ModelConfig.id == model_id).first()
    if not db_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ModelConfig with ID {model_id} not found"
        )

    db_model.name = model_in.name
    db_model.provider_type = model_in.provider_type
    db_model.api_base = model_in.api_base
    db_model.model_name = model_in.model_name
    db_model.command_template = model_in.command_template
    db_model.model_path = model_in.model_path
    db_model.output_format = model_in.output_format
    db_model.enabled = model_in.enabled
    db_model.params_json = model_in.params_json

    db.commit()
    db.refresh(db_model)
    return db_model

@router.delete("/{model_id}")
def delete_model(model_id: int, db: Session = Depends(get_db)):
    """
    Deletes a specific model config.
    Returns HTTP 400 with details if blocked by related voice profiles.
    """
    from app.models import VoiceProfile
    db_model = db.query(ModelConfig).filter(ModelConfig.id == model_id).first()
    if not db_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到该模型配置 (ID: {model_id})"
        )

    related_profiles = db.query(VoiceProfile).filter(VoiceProfile.model_id == model_id).all()
    if related_profiles:
        profile_list = [{"id": p.id, "name": p.name} for p in related_profiles]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "BLOCKED_BY_PROFILES",
                "message": "该模型仍被以下声音配置使用，请先删除或迁移这些声音配置：",
                "profiles": profile_list
            }
        )

    db.delete(db_model)
    db.commit()
    return {"status": "success", "message": "模型配置已删除"}
