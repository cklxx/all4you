"""API routes for Qwen3 Fine-tuner"""

from fastapi import APIRouter
from . import (
    data,
    training,
    models,
    config,
)

router = APIRouter()

# Include sub-routers
router.include_router(data.router, prefix="/data", tags=["Data Management"])
router.include_router(training.router, prefix="/train", tags=["Training"])
router.include_router(models.router, prefix="/models", tags=["Model Management"])
router.include_router(config.router, prefix="/config", tags=["Configuration"])

__all__ = ["router"]
