"""Utility helpers for device and dtype resolution."""

from __future__ import annotations

import os
from typing import Optional, Union

import torch
from loguru import logger

# Shared device options for CLI/config validation
DEVICE_CHOICES = ("auto", "cuda", "mps", "cpu")


def resolve_device(preferred: Optional[str] = None) -> str:
    """Resolve the runtime device from a preferred hint."""
    normalized = (preferred or "auto").lower()

    def _has_mps() -> bool:
        return hasattr(torch.backends, "mps") and torch.backends.mps.is_available()

    if normalized != "auto":
        if normalized.startswith("cuda"):
            if torch.cuda.is_available():
                return "cuda"
            logger.warning("CUDA requested but not available; falling back to auto detection.")
        elif normalized == "mps":
            if _has_mps():
                return "mps"
            logger.warning("MPS requested but not available; falling back to auto detection.")
        elif normalized == "cpu":
            return "cpu"
        else:
            logger.warning("Unknown device '%s'; falling back to auto detection.", normalized)

    if torch.cuda.is_available():
        return "cuda"
    if _has_mps():
        return "mps"
    return "cpu"


def ensure_device_environment(device: str) -> None:
    """Set environment knobs required for specific devices."""
    if device == "mps":
        os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
        os.environ.setdefault("ACCELERATE_USE_MPS_DEVICE", "1")


def coerce_torch_dtype(
    device: str,
    explicit: Optional[Union[str, torch.dtype]] = None,
    prefer_bf16: bool = False,
    prefer_fp16: bool = False,
) -> Optional[torch.dtype]:
    """Determine the torch dtype for the given device and preferences."""
    if isinstance(explicit, torch.dtype):
        return explicit
    if isinstance(explicit, str):
        dtype_attr = getattr(torch, explicit, None)
        if isinstance(dtype_attr, torch.dtype):
            return dtype_attr
        logger.warning("Unsupported torch dtype '%s'; ignoring explicit override.", explicit)

    if device == "mps":
        return torch.float16

    if device.startswith("cuda") and torch.cuda.is_available():
        if prefer_bf16:
            try:
                if torch.cuda.is_bf16_supported():
                    return torch.bfloat16
            except AttributeError:  # pragma: no cover - older torch fallback
                logger.debug("torch.cuda.is_bf16_supported not present; skipping bf16 preference.")
        if prefer_fp16:
            return torch.float16

    return None


def torch_device(device: str) -> torch.device:
    """Convert a device string into a torch.device instance."""
    if device.startswith("cuda"):
        return torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
    return torch.device(device)
