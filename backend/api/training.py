"""
Training API endpoints
Handle training task creation, monitoring, and management
"""

import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from loguru import logger

from core.config import Settings
from core.database import TrainingTask, DataFile, TrainingConfig, get_db
from core.data_processor import DataProcessor
from core.trainer import Trainer_Qwen3, TrainingConfig as TrainerConfig
from models.schemas import (
    TrainingTaskCreate,
    TrainingTaskResponse,
    TrainingTaskUpdate,
    ApiResponse,
)

router = APIRouter()
settings = Settings()

# Store for background task tracking
_training_tasks = {}


async def run_training_task(task_id: str):
    """Background task for training"""
    # Create new database session for background task
    from core.database import SessionLocal
    db_session = SessionLocal()

    try:
        logger.info(f"Starting background training: {task_id}")

        # Get task from database
        task = db_session.query(TrainingTask).filter(TrainingTask.id == task_id).first()
        if not task:
            logger.error(f"Task not found: {task_id}")
            return

        # Update status
        task.status = "running"
        task.started_at = datetime.utcnow()
        db_session.commit()

        # Get data file
        data_file = db_session.query(DataFile).filter(DataFile.id == task.data_file).first()
        if not data_file:
            task.status = "failed"
            task.log_file = "Data file not found"
            db_session.commit()
            return

        # Load data
        logger.info(f"Loading data from: {data_file.file_path}")
        data = DataProcessor.load_and_format_data(
            data_file.file_path,
            data_file.format_type,
            data_file.file_type
        )

        # Create dataset
        hf_dataset = DataProcessor.create_huggingface_dataset(data, data_file.format_type)

        # Create trainer
        trainer_config = TrainerConfig.from_dict(task.config)
        trainer_config.output_dir = str(settings.OUTPUT_DIR / task_id)

        trainer = Trainer_Qwen3(trainer_config)
        trainer.load_model_and_tokenizer()

        # Train
        logger.info("Starting model training...")
        trainer.train(hf_dataset)

        # Save model
        trainer.save_model(trainer_config.output_dir)

        # Update task status
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.output_dir = trainer_config.output_dir

        db_session.commit()

        logger.info(f"Training completed: {task_id}")

    except Exception as e:
        logger.error(f"Training failed for task {task_id}: {str(e)}")
        task.status = "failed"
        task.log_file = str(e)
        db_session.commit()
    finally:
        db_session.close()


@router.post("/start", response_model=TrainingTaskResponse)
async def start_training(
    request: TrainingTaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start a new training task

    This endpoint creates a training task and starts it in the background.
    You can monitor the progress using the status endpoint.
    """
    try:
        logger.info(f"Starting new training task: {request.name}")

        # Validate data file exists
        data_file = db.query(DataFile).filter(DataFile.id == request.data_file_id).first()
        if not data_file:
            raise HTTPException(status_code=404, detail="Data file not found")

        # Validate config exists
        config = db.query(TrainingConfig).filter(TrainingConfig.id == request.config_id).first()
        if not config:
            raise HTTPException(status_code=404, detail="Training config not found")

        # Create training task
        task_id = str(uuid.uuid4())
        task = TrainingTask(
            id=task_id,
            name=request.name,
            model_name=config.model_name,
            data_file=request.data_file_id,
            config_file=request.config_id,
            status="pending",
            config=config.config,
            created_at=datetime.utcnow()
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        # Add background task
        background_tasks.add_task(run_training_task, task_id)

        logger.info(f"Training task created: {task_id}")

        return TrainingTaskResponse(
            id=task.id,
            name=task.name,
            model_name=task.model_name,
            status=task.status,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            total_steps=task.total_steps,
            completed_steps=task.completed_steps,
            current_loss=task.current_loss,
            best_loss=task.best_loss,
            output_dir=task.output_dir,
            log_file=task.log_file
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting training: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}", response_model=TrainingTaskResponse)
async def get_training_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Get training task status"""
    try:
        task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return TrainingTaskResponse(
            id=task.id,
            name=task.name,
            model_name=task.model_name,
            status=task.status,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            total_steps=task.total_steps,
            completed_steps=task.completed_steps,
            current_loss=task.current_loss,
            best_loss=task.best_loss,
            output_dir=task.output_dir,
            log_file=task.log_file
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_training_tasks(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
) -> ApiResponse:
    """List training tasks"""
    try:
        query = db.query(TrainingTask)

        if status:
            query = query.filter(TrainingTask.status == status)

        total = query.count()
        tasks = query.offset(skip).limit(limit).all()

        task_list = [
            {
                "id": t.id,
                "name": t.name,
                "model_name": t.model_name,
                "status": t.status,
                "created_at": t.created_at,
                "started_at": t.started_at,
                "completed_at": t.completed_at,
                "progress": {
                    "total_steps": t.total_steps,
                    "completed_steps": t.completed_steps,
                    "current_loss": t.current_loss,
                    "best_loss": t.best_loss
                }
            }
            for t in tasks
        ]

        return ApiResponse(
            success=True,
            message="Training tasks listed successfully",
            data={
                "total": total,
                "skip": skip,
                "limit": limit,
                "tasks": task_list
            }
        )

    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{task_id}")
async def update_training_task(
    task_id: str,
    update: TrainingTaskUpdate,
    db: Session = Depends(get_db)
) -> TrainingTaskResponse:
    """Update training task"""
    try:
        task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Only allow updates to certain fields
        if update.status:
            task.status = update.status
        if update.completed_steps is not None:
            task.completed_steps = update.completed_steps
        if update.current_loss is not None:
            task.current_loss = update.current_loss
        if update.best_loss is not None:
            task.best_loss = update.best_loss

        db.commit()
        db.refresh(task)

        return TrainingTaskResponse(
            id=task.id,
            name=task.name,
            model_name=task.model_name,
            status=task.status,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            total_steps=task.total_steps,
            completed_steps=task.completed_steps,
            current_loss=task.current_loss,
            best_loss=task.best_loss,
            output_dir=task.output_dir,
            log_file=task.log_file
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}")
async def delete_training_task(
    task_id: str,
    db: Session = Depends(get_db)
) -> ApiResponse:
    """Delete training task"""
    try:
        task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        db.delete(task)
        db.commit()

        logger.info(f"Training task deleted: {task_id}")

        return ApiResponse(
            success=True,
            message=f"Training task {task_id} deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
