"""
Configuration management for Qwen3 Fine-tuner
"""

from pathlib import Path
from typing import Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings"""

    # Server config
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./qwen3_finetuner.db"

    # Model config
    DEFAULT_MODEL: str = "Qwen/Qwen3-4B"  # Primary production model
    RECOMMENDED_MODELS: list = ["Qwen/Qwen3-4B", "Qwen/Qwen3-0.6B"]  # 4B for production, 0.6B for quick validation
    HF_TOKEN: Optional[str] = None
    USE_MODELSCOPE: bool = True  # Use ModelScope for faster download in China
    MODEL_CACHE_DIR: Optional[str] = None  # None = use default cache

    # Training config
    DEFAULT_LEARNING_RATE: float = 2e-4
    DEFAULT_BATCH_SIZE: int = 4
    DEFAULT_GRADIENT_ACCUMULATION_STEPS: int = 4
    DEFAULT_NUM_EPOCHS: int = 3
    DEFAULT_MAX_STEPS: int = -1

    # Path config
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = Path(__file__).parent.parent / "data"
    OUTPUT_DIR: Path = Path(__file__).parent.parent / "outputs"
    CONFIG_DIR: Path = Path(__file__).parent.parent / "configs"
    LOG_DIR: Path = Path(__file__).parent.parent / "logs"

    # GPU config
    GPU_MEMORY_FRACTION: float = 0.95
    USE_MIXED_PRECISION: bool = True
    GRADIENT_CHECKPOINTING: bool = True

    # Feature flags
    USE_UNSLOTH: bool = True
    USE_FLASH_ATTENTION: bool = True
    USE_QUANTIZATION: bool = False
    QUANTIZATION_BITS: int = 4  # 4 or 8

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        arbitrary_types_allowed=True
    )

    @model_validator(mode='after')
    def create_directories(self) -> 'Settings':
        """Create directories if they don't exist"""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        return self
