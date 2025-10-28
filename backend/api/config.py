"""
Configuration management API endpoints
Handle training configuration templates
"""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from loguru import logger

from core.database import TrainingConfig, get_db
from models.schemas import TrainingConfigCreate, TrainingConfigResponse, ApiResponse

router = APIRouter()

# Default configurations
DEFAULT_CONFIGS = {
    "qwen3-lora-default": {
        "name": "Qwen3 LoRA Default",
        "description": "Default LoRA configuration optimized for Qwen3-4B",
        "model_name": "Qwen/Qwen3-4B",
        "training_method": "lora",
        "config": {
            "num_train_epochs": 3,
            "per_device_train_batch_size": 4,
            "per_device_eval_batch_size": 4,
            "gradient_accumulation_steps": 4,
            "learning_rate": 2e-4,
            "max_seq_length": 2048,
            "lora_rank": 64,
            "lora_alpha": 128,
            "lora_dropout": 0.05,
            "load_in_4bit": True,
            "use_flash_attention": True,
            "gradient_checkpointing": True,
        },
        "is_default": True
    },
    "qwen3-qlora-fast": {
        "name": "Qwen3 QLoRA Fast",
        "description": "QLoRA configuration tuned for Qwen3-4B, balancing memory usage and training speed",
        "model_name": "Qwen/Qwen3-4B",
        "training_method": "qlora",
        "config": {
            "num_train_epochs": 2,
            "per_device_train_batch_size": 2,
            "per_device_eval_batch_size": 2,
            "gradient_accumulation_steps": 8,
            "learning_rate": 1e-4,
            "max_seq_length": 2048,
            "lora_rank": 32,
            "lora_alpha": 64,
            "lora_dropout": 0.05,
            "load_in_4bit": True,
            "use_flash_attention": True,
            "gradient_checkpointing": True,
        },
        "is_default": False
    },
    "qwen3-sft-full": {
        "name": "Qwen3 SFT Full",
        "description": "Full fine-tuning configuration targeting the Qwen3-4B base model",
        "model_name": "Qwen/Qwen3-4B",
        "training_method": "sft",
        "config": {
            "num_train_epochs": 3,
            "per_device_train_batch_size": 8,
            "per_device_eval_batch_size": 8,
            "gradient_accumulation_steps": 2,
            "learning_rate": 5e-5,
            "max_seq_length": 2048,
            "load_in_4bit": False,
            "use_flash_attention": True,
            "gradient_checkpointing": True,
        },
        "is_default": False
    },
    "qwen3-dpo-preference": {
        "name": "Qwen3 DPO Preference",
        "description": "Direct Preference Optimization preset for Qwen3-4B alignment training",
        "model_name": "Qwen/Qwen3-4B",
        "training_method": "dpo",
        "config": {
            "num_train_epochs": 1,
            "per_device_train_batch_size": 4,
            "per_device_eval_batch_size": 4,
            "gradient_accumulation_steps": 4,
            "learning_rate": 1e-4,
            "max_seq_length": 2048,
            "load_in_4bit": True,
            "use_flash_attention": True,
            "gradient_checkpointing": True,
        },
        "is_default": False
    },
}


def init_default_configs(db: Session):
    """Initialize default configurations in database"""
    try:
        # Check if defaults already exist
        existing = db.query(TrainingConfig).filter(TrainingConfig.is_default == 1).count()
        if existing > 0:
            return

        for config_id, config_data in DEFAULT_CONFIGS.items():
            db_config = TrainingConfig(
                id=config_id,
                name=config_data["name"],
                description=config_data["description"],
                model_name=config_data["model_name"],
                training_method=config_data["training_method"],
                config=config_data["config"],
                is_default=config_data["is_default"]
            )
            db.add(db_config)

        db.commit()
        logger.info("Default configurations initialized")
    except Exception as e:
        logger.error(f"Error initializing default configs: {str(e)}")


@router.get("/list")
async def list_configs(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
) -> ApiResponse:
    """List all training configurations"""
    try:
        # Initialize defaults if needed
        init_default_configs(db)

        total = db.query(TrainingConfig).count()
        configs = db.query(TrainingConfig).offset(skip).limit(limit).all()

        config_list = [
            TrainingConfigResponse(
                id=c.id,
                name=c.name,
                description=c.description,
                model_name=c.model_name,
                training_method=c.training_method,
                is_default=bool(c.is_default),
                config=c.config,
                created_at=c.created_at
            )
            for c in configs
        ]

        return ApiResponse(
            success=True,
            message="Configurations listed successfully",
            data={
                "total": total,
                "skip": skip,
                "limit": limit,
                "configs": [c.model_dump() for c in config_list]
            }
        )

    except Exception as e:
        logger.error(f"Error listing configs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{config_id}")
async def get_config(
    config_id: str,
    db: Session = Depends(get_db)
) -> TrainingConfigResponse:
    """Get specific training configuration"""
    try:
        # Initialize defaults if needed
        init_default_configs(db)

        config = db.query(TrainingConfig).filter(TrainingConfig.id == config_id).first()
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")

        return TrainingConfigResponse(
            id=config.id,
            name=config.name,
            description=config.description,
            model_name=config.model_name,
            training_method=config.training_method,
            is_default=bool(config.is_default),
            config=config.config,
            created_at=config.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create", response_model=TrainingConfigResponse)
async def create_config(
    request: TrainingConfigCreate,
    db: Session = Depends(get_db)
):
    """Create new training configuration"""
    try:
        # Check if name already exists
        existing = db.query(TrainingConfig).filter(TrainingConfig.name == request.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Configuration name already exists")

        config_id = str(uuid.uuid4())

        # Build config dict from request
        config_dict = {
            "num_train_epochs": request.num_train_epochs,
            "per_device_train_batch_size": request.per_device_train_batch_size,
            "per_device_eval_batch_size": request.per_device_eval_batch_size,
            "gradient_accumulation_steps": request.gradient_accumulation_steps,
            "learning_rate": request.learning_rate,
            "max_seq_length": request.max_seq_length,
            "lora_rank": request.lora_rank,
            "lora_alpha": request.lora_alpha,
            "lora_dropout": request.lora_dropout,
            "load_in_4bit": request.load_in_4bit,
            "use_flash_attention": request.use_flash_attention,
            "gradient_checkpointing": request.gradient_checkpointing,
        }

        db_config = TrainingConfig(
            id=config_id,
            name=request.name,
            description=request.description,
            model_name=request.model_name,
            training_method=request.training_method,
            config=config_dict,
            is_default=0
        )

        db.add(db_config)
        db.commit()
        db.refresh(db_config)

        logger.info(f"Training configuration created: {config_id}")

        return TrainingConfigResponse(
            id=db_config.id,
            name=db_config.name,
            description=db_config.description,
            model_name=db_config.model_name,
            training_method=db_config.training_method,
            is_default=bool(db_config.is_default),
            config=db_config.config,
            created_at=db_config.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{config_id}")
async def delete_config(
    config_id: str,
    db: Session = Depends(get_db)
) -> ApiResponse:
    """Delete training configuration"""
    try:
        config = db.query(TrainingConfig).filter(TrainingConfig.id == config_id).first()
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")

        if config.is_default:
            raise HTTPException(status_code=400, detail="Cannot delete default configuration")

        db.delete(config)
        db.commit()

        logger.info(f"Training configuration deleted: {config_id}")

        return ApiResponse(
            success=True,
            message=f"Configuration {config_id} deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/defaults/all")
async def get_default_configs() -> ApiResponse:
    """Get all default configurations"""
    return ApiResponse(
        success=True,
        message="Default configurations",
        data={
            "defaults": [
                {
                    "id": cid,
                    "name": c["name"],
                    "description": c["description"],
                    "model_name": c["model_name"],
                    "training_method": c["training_method"],
                }
                for cid, c in DEFAULT_CONFIGS.items()
            ]
        }
    )
