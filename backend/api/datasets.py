"""
Dataset download API endpoints
Handle dataset download from ModelScope
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from loguru import logger
from typing import Optional, Dict, Any
from pathlib import Path
import uuid

from models.schemas import ApiResponse
from core.dataset_hub import ModelScopeDatasetManager
from core.config import Settings

router = APIRouter()
settings = Settings()

# Track download tasks
download_tasks: Dict[str, Dict[str, Any]] = {}


@router.get("/presets")
async def list_dataset_presets() -> ApiResponse:
    """List all available dataset presets"""
    try:
        presets = ModelScopeDatasetManager.list_presets()

        # Format presets for frontend
        formatted_presets = []
        for name, info in presets.items():
            formatted_presets.append({
                "name": name,
                "dataset_id": info["dataset_id"],
                "split": info["split"],
                "subset": info.get("subset"),
                "description": info.get("description", ""),
                "fields": info.get("fields", {})
            })

        return ApiResponse(
            success=True,
            message="Dataset presets listed successfully",
            data={
                "total": len(formatted_presets),
                "presets": formatted_presets
            }
        )

    except Exception as e:
        logger.error(f"Error listing dataset presets: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download")
async def download_dataset(
    background_tasks: BackgroundTasks,
    name_or_id: str,
    split: Optional[str] = None,
    subset: Optional[str] = None,
    limit: Optional[int] = None,
) -> ApiResponse:
    """
    Download a dataset from ModelScope

    Args:
        name_or_id: Preset name or ModelScope dataset ID
        split: Dataset split (train/test/validation)
        subset: Optional subset name
        limit: Limit number of samples

    Returns:
        Task ID for tracking download progress
    """
    try:
        # Generate task ID
        task_id = str(uuid.uuid4())

        # Initialize task status
        download_tasks[task_id] = {
            "id": task_id,
            "name_or_id": name_or_id,
            "split": split,
            "subset": subset,
            "limit": limit,
            "status": "pending",
            "progress": 0,
            "message": "Download queued",
            "output_path": None,
            "error": None
        }

        # Add download task to background
        background_tasks.add_task(
            _download_dataset_task,
            task_id,
            name_or_id,
            split,
            subset,
            limit
        )

        return ApiResponse(
            success=True,
            message=f"Dataset download started: {name_or_id}",
            data={
                "task_id": task_id,
                "status": "pending"
            }
        )

    except Exception as e:
        logger.error(f"Error starting dataset download: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{task_id}")
async def get_download_status(task_id: str) -> ApiResponse:
    """Get download task status"""
    try:
        if task_id not in download_tasks:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        task = download_tasks[task_id]

        return ApiResponse(
            success=True,
            message="Task status retrieved",
            data=task
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting download status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/downloads/list")
async def list_download_tasks() -> ApiResponse:
    """List all download tasks"""
    try:
        tasks = list(download_tasks.values())

        return ApiResponse(
            success=True,
            message="Download tasks listed",
            data={
                "total": len(tasks),
                "tasks": tasks
            }
        )

    except Exception as e:
        logger.error(f"Error listing download tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/download/{task_id}")
async def cancel_download(task_id: str) -> ApiResponse:
    """Cancel a download task"""
    try:
        if task_id not in download_tasks:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        task = download_tasks[task_id]

        if task["status"] == "completed":
            # If completed, just remove from list
            del download_tasks[task_id]
            return ApiResponse(
                success=True,
                message="Task removed"
            )
        elif task["status"] in ["pending", "running"]:
            # Mark as cancelled (actual cancellation is best-effort)
            task["status"] = "cancelled"
            task["message"] = "Download cancelled by user"
            return ApiResponse(
                success=True,
                message="Task cancelled"
            )
        else:
            # Already completed, failed, or cancelled
            return ApiResponse(
                success=True,
                message=f"Task already in {task['status']} state"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling download: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def _download_dataset_task(
    task_id: str,
    name_or_id: str,
    split: Optional[str],
    subset: Optional[str],
    limit: Optional[int]
):
    """Background task to download dataset"""
    try:
        # Update status
        download_tasks[task_id]["status"] = "running"
        download_tasks[task_id]["message"] = "Downloading dataset..."
        download_tasks[task_id]["progress"] = 10

        # Initialize dataset manager
        manager = ModelScopeDatasetManager(cache_dir="backend/data/datasets")

        # Update progress
        download_tasks[task_id]["progress"] = 30
        download_tasks[task_id]["message"] = "Loading dataset configuration..."

        # Download and convert dataset
        output_path, metadata = manager.download_and_convert(
            name_or_id=name_or_id,
            split=split,
            subset=subset,
            limit=limit
        )

        # Update progress
        download_tasks[task_id]["progress"] = 90
        download_tasks[task_id]["message"] = "Finalizing download..."

        # Complete
        download_tasks[task_id].update({
            "status": "completed",
            "progress": 100,
            "message": f"Dataset downloaded successfully: {metadata['total_samples']} samples",
            "output_path": str(output_path),
            "metadata": {
                "total_samples": metadata["total_samples"],
                "format": metadata.get("format", "alpaca"),
                "dataset_id": metadata.get("dataset_id"),
                "split": metadata.get("split")
            }
        })

        logger.info(f"Dataset download completed: {task_id}")

    except Exception as e:
        logger.error(f"Dataset download failed: {str(e)}")
        download_tasks[task_id].update({
            "status": "failed",
            "progress": 0,
            "message": f"Download failed: {str(e)}",
            "error": str(e)
        })
