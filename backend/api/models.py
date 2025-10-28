"""
Model management API endpoints
Handle model information and download
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from models.schemas import ModelInfo, ApiResponse
from core.model_manager import get_model_manager
from core.config import Settings

router = APIRouter()
settings = Settings()

# Predefined models
AVAILABLE_MODELS = {
    "Qwen/Qwen3-0.6B": {
        "model_name": "Qwen/Qwen3-0.6B",
        "model_size": "0.6B",
        "parameters": 600_000_000,
        "max_seq_length": 2048,
        "description": "【推荐】超小型 Qwen3 模型，适合快速实验和资源受限环境，训练速度快",
        "supported_training_methods": ["sft", "lora", "qlora"],
        "recommended": True
    },
    "Qwen/Qwen3-0.5B": {
        "model_name": "Qwen/Qwen3-0.5B",
        "model_size": "0.5B",
        "parameters": 500_000_000,
        "max_seq_length": 2048,
        "description": "超小型 Qwen3 模型，适合边缘设备部署",
        "supported_training_methods": ["sft", "lora", "qlora"]
    },
    "Qwen/Qwen3-1.8B": {
        "model_name": "Qwen/Qwen3-1.8B",
        "model_size": "1.8B",
        "parameters": 1_800_000_000,
        "max_seq_length": 2048,
        "description": "Small Qwen3 model, good for mobile and resource-constrained environments",
        "supported_training_methods": ["sft", "lora", "qlora"]
    },
    "Qwen/Qwen3-3B": {
        "model_name": "Qwen/Qwen3-3B",
        "model_size": "3B",
        "parameters": 3_000_000_000,
        "max_seq_length": 2048,
        "description": "小型 Qwen3 模型，性能良好",
        "supported_training_methods": ["sft", "lora", "qlora"]
    },
    "Qwen/Qwen3-4B": {
        "model_name": "Qwen/Qwen3-4B",
        "model_size": "4B",
        "parameters": 4_000_000_000,
        "max_seq_length": 2048,
        "description": "【推荐】中等规模 Qwen3 模型，性能和速度的最佳平衡，适合大多数应用场景",
        "supported_training_methods": ["sft", "lora", "qlora", "dpo"],
        "recommended": True
    },
    "Qwen/Qwen3-7B": {
        "model_name": "Qwen/Qwen3-7B",
        "model_size": "7B",
        "parameters": 7_000_000_000,
        "max_seq_length": 2048,
        "description": "Mid-size Qwen3 model, recommended for most use cases",
        "supported_training_methods": ["sft", "lora", "qlora", "dpo"]
    },
    "Qwen/Qwen3-14B": {
        "model_name": "Qwen/Qwen3-14B",
        "model_size": "14B",
        "parameters": 14_000_000_000,
        "max_seq_length": 2048,
        "description": "Large Qwen3 model with improved performance",
        "supported_training_methods": ["sft", "lora", "qlora", "dpo", "grpo"]
    },
    "Qwen/Qwen3-14B-Instruct": {
        "model_name": "Qwen/Qwen3-14B-Instruct",
        "model_size": "14B",
        "parameters": 14_000_000_000,
        "max_seq_length": 2048,
        "description": "Instruction-tuned 14B Qwen3 model",
        "supported_training_methods": ["sft", "lora", "qlora", "dpo", "grpo"]
    },
    "Qwen/Qwen3-30B-A3B": {
        "model_name": "Qwen/Qwen3-30B-A3B",
        "model_size": "30B (A3B MoE)",
        "parameters": 30_000_000_000,
        "max_seq_length": 2048,
        "description": "Large Mixture-of-Experts model with 30B total parameters",
        "supported_training_methods": ["sft", "lora", "qlora", "dpo", "grpo"]
    },
}


@router.get("/list")
async def list_available_models() -> ApiResponse:
    """List all available models for fine-tuning"""
    try:
        models = [
            ModelInfo(**model_info)
            for model_info in AVAILABLE_MODELS.values()
        ]

        return ApiResponse(
            success=True,
            message="Available models listed successfully",
            data={
                "total": len(models),
                "models": [m.model_dump() for m in models]
            }
        )

    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{model_name}")
async def get_model_info(model_name: str) -> ModelInfo:
    """Get information about a specific model"""
    try:
        # URL decode model name
        model_name = model_name.replace("_", "/")

        if model_name not in AVAILABLE_MODELS:
            raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")

        return ModelInfo(**AVAILABLE_MODELS[model_name])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info/supported-methods")
async def get_supported_training_methods() -> ApiResponse:
    """Get list of supported training methods"""
    methods = {
        "sft": "Supervised Fine-Tuning - Train on instruction-output pairs",
        "lora": "LoRA - Parameter-efficient fine-tuning with low rank adaptation",
        "qlora": "QLoRA - Quantized LoRA for 4-bit training with reduced memory",
        "dpo": "Direct Preference Optimization - Align model with preferences",
        "grpo": "Group Relative Policy Optimization - Efficient preference optimization",
    }

    return ApiResponse(
        success=True,
        message="Supported training methods",
        data=methods
    )


@router.post("/download")
async def download_model(model_name: str, force: bool = False) -> ApiResponse:
    """
    Download a model and cache it locally

    Args:
        model_name: Model name (e.g., Qwen/Qwen3-0.6B)
        force: Force re-download even if cached

    Returns:
        Download status and cache information
    """
    try:
        # URL decode model name
        model_name = model_name.replace("_", "/")

        if model_name not in AVAILABLE_MODELS:
            raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")

        # Get model manager
        model_manager = get_model_manager(
            cache_dir=settings.MODEL_CACHE_DIR,
            use_modelscope=settings.USE_MODELSCOPE
        )

        # Check if already cached
        if not force:
            cached_path = model_manager.get_model_cache_path(model_name)
            if cached_path:
                return ApiResponse(
                    success=True,
                    message=f"Model already cached: {model_name}",
                    data={
                        "model_name": model_name,
                        "status": "cached",
                        "path": str(cached_path)
                    }
                )

        # Download and cache
        logger.info(f"Downloading model: {model_name}")
        cache_path = model_manager.ensure_model_cached(
            model_name,
            force_download=force
        )

        return ApiResponse(
            success=True,
            message=f"Model downloaded and cached: {model_name}",
            data={
                "model_name": model_name,
                "status": "cached",
                "path": cache_path,
                "source": "modelscope" if settings.USE_MODELSCOPE else "huggingface"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading model: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/list")
async def list_cached_models() -> ApiResponse:
    """List all cached models"""
    try:
        model_manager = get_model_manager(
            cache_dir=settings.MODEL_CACHE_DIR,
            use_modelscope=settings.USE_MODELSCOPE
        )

        cached = model_manager.list_cached_models()

        return ApiResponse(
            success=True,
            message="Cached models listed successfully",
            data={
                "total": len(cached),
                "models": cached,
                "cache_dir": str(model_manager.cache_dir)
            }
        )

    except Exception as e:
        logger.error(f"Error listing cached models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache/{model_name}")
async def clear_model_cache(model_name: str) -> ApiResponse:
    """Clear cache for specific model"""
    try:
        # URL decode model name
        model_name = model_name.replace("_", "/")

        model_manager = get_model_manager(
            cache_dir=settings.MODEL_CACHE_DIR,
            use_modelscope=settings.USE_MODELSCOPE
        )

        model_manager.clear_cache(model_name)

        return ApiResponse(
            success=True,
            message=f"Cache cleared for model: {model_name}"
        )

    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache/all")
async def clear_all_cache() -> ApiResponse:
    """Clear all model cache"""
    try:
        model_manager = get_model_manager(
            cache_dir=settings.MODEL_CACHE_DIR,
            use_modelscope=settings.USE_MODELSCOPE
        )

        model_manager.clear_cache()

        return ApiResponse(
            success=True,
            message="All model cache cleared"
        )

    except Exception as e:
        logger.error(f"Error clearing all cache: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
