"""
Model Manager with ModelScope support and caching
Supports both Hugging Face Hub and ModelScope (魔搭)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

# Provide backward compatibility for missing symbols in new Hugging Face Datasets.
try:  # pragma: no cover - optional dependency
    import datasets  # type: ignore
    from datasets import load as _hf_load  # type: ignore

    factory = getattr(_hf_load, "HubDatasetModuleFactory", None)
    if factory is not None:
        if not hasattr(_hf_load, "HubDatasetModuleFactoryWithoutScript"):
            _hf_load.HubDatasetModuleFactoryWithoutScript = factory  # type: ignore[attr-defined]
        if not hasattr(_hf_load, "HubDatasetModuleFactoryWithScript"):
            _hf_load.HubDatasetModuleFactoryWithScript = factory  # type: ignore[attr-defined]
    local_factory = getattr(_hf_load, "LocalDatasetModuleFactory", None)
    if local_factory is not None:
        if not hasattr(_hf_load, "LocalDatasetModuleFactoryWithoutScript"):
            _hf_load.LocalDatasetModuleFactoryWithoutScript = local_factory  # type: ignore[attr-defined]
        if not hasattr(_hf_load, "LocalDatasetModuleFactoryWithScript"):
            _hf_load.LocalDatasetModuleFactoryWithScript = local_factory  # type: ignore[attr-defined]
    if not hasattr(datasets, "LargeList"):
        try:
            from datasets.features import Sequence as _Sequence  # type: ignore
        except Exception:
            _Sequence = None  # type: ignore
        if _Sequence is not None:
            datasets.LargeList = _Sequence  # type: ignore[attr-defined]

    from datasets import data_files as _hf_data_files  # type: ignore
    if not hasattr(_hf_data_files, "get_metadata_patterns") and hasattr(
        _hf_data_files, "get_data_patterns"
    ):
        _hf_data_files.get_metadata_patterns = _hf_data_files.get_data_patterns  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - optional dependency
    pass

try:
    from modelscope import snapshot_download
    HAS_MODELSCOPE = True
except ImportError:
    HAS_MODELSCOPE = False
    logger.warning("ModelScope not installed, will use Hugging Face Hub only")

from transformers import AutoModelForCausalLM, AutoTokenizer

from .devices import (
    resolve_device,
    ensure_device_environment,
    coerce_torch_dtype,
    torch_device,
)


class ModelManager:
    """
    Unified model manager supporting both Hugging Face and ModelScope
    Implements intelligent caching and automatic fallback
    """

    # ModelScope ID mapping for Qwen models
    MODELSCOPE_MAP = {
        "Qwen/Qwen3-0.5B": "Qwen/Qwen3-0.5B",
        "Qwen/Qwen3-0.6B": "Qwen/Qwen3-0.6B",
        "Qwen/Qwen3-1.8B": "Qwen/Qwen3-1.8B",
        "Qwen/Qwen3-3B": "Qwen/Qwen3-3B",
        "Qwen/Qwen3-4B": "Qwen/Qwen3-4B",
        "Qwen/Qwen3-7B": "Qwen/Qwen3-7B",
        "Qwen/Qwen3-14B": "Qwen/Qwen3-14B",
        "Qwen/Qwen3-14B-Instruct": "Qwen/Qwen3-14B-Instruct",
    }

    def __init__(self, cache_dir: Optional[str] = None, use_modelscope: bool = True):
        """
        Initialize model manager

        Args:
            cache_dir: Directory for model cache. If None, uses default cache.
            use_modelscope: Whether to prefer ModelScope for downloads (faster in China)
        """
        self.use_modelscope = use_modelscope and HAS_MODELSCOPE
        self.cache_dir = Path(cache_dir) if cache_dir else self._get_default_cache_dir()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Model cache directory: {self.cache_dir}")
        logger.info(f"Using ModelScope: {self.use_modelscope}")

    @staticmethod
    def _get_default_cache_dir() -> Path:
        """Get default cache directory"""
        # Use environment variable or default
        if "MODEL_CACHE_DIR" in os.environ:
            return Path(os.environ["MODEL_CACHE_DIR"])

        # Default to ~/.cache/qwen3-finetuner/models
        return Path.home() / ".cache" / "qwen3-finetuner" / "models"

    def get_model_cache_path(self, model_name: str) -> Optional[Path]:
        """
        Check if model is already cached

        Args:
            model_name: Model name or ID

        Returns:
            Path to cached model if exists, None otherwise
        """
        # Clean model name for directory
        cache_name = model_name.replace("/", "--")
        model_path = self.cache_dir / cache_name

        if model_path.exists() and (model_path / "config.json").exists():
            logger.info(f"Model found in cache: {model_path}")
            return model_path

        return None

    def download_from_modelscope(
        self,
        model_name: str,
        revision: str = "master",
        **kwargs
    ) -> str:
        """
        Download model from ModelScope

        Args:
            model_name: Model name in ModelScope
            revision: Model version/revision
            **kwargs: Additional arguments for snapshot_download

        Returns:
            Path to downloaded model
        """
        if not HAS_MODELSCOPE:
            raise RuntimeError("ModelScope not installed. Install with: pip install modelscope")

        logger.info(f"Downloading model from ModelScope: {model_name}")

        # Get ModelScope ID
        ms_model_id = self.MODELSCOPE_MAP.get(model_name, model_name)

        # Download to cache
        cache_name = model_name.replace("/", "--")
        local_path = self.cache_dir / cache_name

        try:
            model_dir = snapshot_download(
                ms_model_id,
                cache_dir=str(self.cache_dir),
                revision=revision,
                **kwargs
            )
            logger.info(f"Model downloaded to: {model_dir}")
            return model_dir
        except Exception as e:
            logger.error(f"ModelScope download failed: {str(e)}")
            raise

    def download_from_huggingface(
        self,
        model_name: str,
        **kwargs
    ) -> str:
        """
        Download model from Hugging Face Hub

        Args:
            model_name: Model name in Hugging Face
            **kwargs: Additional arguments

        Returns:
            Path to downloaded model
        """
        logger.info(f"Downloading model from Hugging Face: {model_name}")

        # Transformers will handle caching automatically
        # Just trigger the download by loading config
        from transformers import AutoConfig

        token = os.getenv("HF_TOKEN")
        config = AutoConfig.from_pretrained(
            model_name,
            cache_dir=str(self.cache_dir),
            token=token,
            **kwargs
        )

        # Get cache path
        cache_name = model_name.replace("/", "--")
        return str(self.cache_dir / cache_name)

    def ensure_model_cached(
        self,
        model_name: str,
        force_download: bool = False,
        **kwargs
    ) -> str:
        """
        Ensure model is cached locally, download if necessary

        Args:
            model_name: Model name
            force_download: Force re-download even if cached
            **kwargs: Additional download arguments

        Returns:
            Path to cached model
        """
        # Check cache first
        if not force_download:
            cached_path = self.get_model_cache_path(model_name)
            if cached_path:
                return str(cached_path)

        # Download if not cached
        logger.info(f"Model not in cache, downloading: {model_name}")

        # Try ModelScope first (if enabled and in China)
        if self.use_modelscope and model_name in self.MODELSCOPE_MAP:
            try:
                return self.download_from_modelscope(model_name, **kwargs)
            except Exception as e:
                logger.warning(f"ModelScope download failed, falling back to Hugging Face: {str(e)}")

        # Fall back to Hugging Face
        return self.download_from_huggingface(model_name, **kwargs)

    def load_model_and_tokenizer(
        self,
        model_name: str,
        device_map: Optional[str] = "auto",
        trust_remote_code: bool = True,
        device: Optional[str] = None,
        torch_dtype: Optional["torch.dtype"] = None,
        **kwargs
    ) -> tuple:
        """
        Load model and tokenizer with caching

        Args:
            model_name: Model name
            device_map: Device mapping strategy
            trust_remote_code: Whether to trust remote code
            **kwargs: Additional arguments for model loading

        Returns:
            Tuple of (model, tokenizer)
        """
        logger.info(f"Loading model: {model_name}")

        resolved_device = resolve_device(device or device_map)
        ensure_device_environment(resolved_device)
        dtype = coerce_torch_dtype(resolved_device, explicit=torch_dtype)
        torch_dev = torch_device(resolved_device)

        # Ensure model is cached
        model_path = self.ensure_model_cached(model_name)

        # Load tokenizer
        token = os.getenv("HF_TOKEN")
        tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=trust_remote_code,
            token=token,
        )

        # Set pad token if not set
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # Load model
        effective_device_map = device_map
        if resolved_device in {"cpu", "mps"}:
            effective_device_map = None

        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map=effective_device_map,
            trust_remote_code=trust_remote_code,
            token=token,
            torch_dtype=dtype,
            **kwargs
        )

        if effective_device_map is None:
            model.to(torch_dev)
        elif resolved_device.startswith("cuda"):
            model.to(torch_dev)

        logger.info(f"Model loaded successfully from {model_path}")
        return model, tokenizer

    def list_cached_models(self) -> list:
        """
        List all cached models

        Returns:
            List of cached model names
        """
        if not self.cache_dir.exists():
            return []

        cached = []
        for item in self.cache_dir.iterdir():
            if item.is_dir() and (item / "config.json").exists():
                # Convert directory name back to model name
                model_name = item.name.replace("--", "/")
                cached.append({
                    "model_name": model_name,
                    "path": str(item),
                    "size": self._get_dir_size(item)
                })

        return cached

    @staticmethod
    def _get_dir_size(path: Path) -> int:
        """Get directory size in bytes"""
        total = 0
        for file in path.rglob("*"):
            if file.is_file():
                total += file.stat().st_size
        return total

    def clear_cache(self, model_name: Optional[str] = None):
        """
        Clear model cache

        Args:
            model_name: Specific model to clear. If None, clears all.
        """
        if model_name:
            cache_name = model_name.replace("/", "--")
            model_path = self.cache_dir / cache_name
            if model_path.exists():
                import shutil
                shutil.rmtree(model_path)
                logger.info(f"Cleared cache for: {model_name}")
        else:
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                logger.info("Cleared all model cache")


# Global model manager instance
_model_manager = None


def get_model_manager(
    cache_dir: Optional[str] = None,
    use_modelscope: bool = True
) -> ModelManager:
    """
    Get global model manager instance

    Args:
        cache_dir: Custom cache directory
        use_modelscope: Whether to use ModelScope

    Returns:
        ModelManager instance
    """
    global _model_manager

    if _model_manager is None:
        _model_manager = ModelManager(
            cache_dir=cache_dir,
            use_modelscope=use_modelscope
        )

    return _model_manager
