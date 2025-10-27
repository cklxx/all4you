"""
Pydantic schemas for API requests and responses
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# ============ Data File Schemas ============
class DataFileCreate(BaseModel):
    """Create data file request"""
    filename: str = Field(..., description="File name")
    file_type: str = Field(..., description="File type: json, jsonl, csv, txt")
    format_type: str = Field(default="alpaca", description="Data format: alpaca, sharegpt, raw")


class DataFileResponse(BaseModel):
    """Data file response"""
    id: str
    filename: str
    file_type: str
    format_type: str
    total_samples: int
    file_size: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Training Config Schemas ============
class TrainingConfigCreate(BaseModel):
    """Create training config request"""
    name: str = Field(..., description="Config name")
    description: Optional[str] = None
    model_name: str = Field(default="Qwen/Qwen3-7B-Instruct")
    training_method: str = Field(default="lora", description="sft, lora, qlora, dpo, grpo")

    # Training parameters
    num_train_epochs: int = Field(default=3)
    per_device_train_batch_size: int = Field(default=4)
    per_device_eval_batch_size: int = Field(default=4)
    gradient_accumulation_steps: int = Field(default=4)
    learning_rate: float = Field(default=2e-4)
    max_seq_length: int = Field(default=2048)

    # LoRA parameters
    lora_rank: int = Field(default=64)
    lora_alpha: int = Field(default=128)
    lora_dropout: float = Field(default=0.05)

    # Quantization
    load_in_4bit: bool = Field(default=True)
    use_flash_attention: bool = Field(default=True)
    gradient_checkpointing: bool = Field(default=True)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Qwen3 LoRA Default",
                "description": "Default LoRA configuration for Qwen3",
                "model_name": "Qwen/Qwen3-7B-Instruct",
                "training_method": "lora",
                "num_train_epochs": 3,
                "per_device_train_batch_size": 4,
                "learning_rate": 0.0002,
                "lora_rank": 64,
                "lora_alpha": 128,
            }
        }


class TrainingConfigResponse(BaseModel):
    """Training config response"""
    id: str
    name: str
    description: Optional[str]
    model_name: str
    training_method: str
    is_default: bool
    config: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Training Task Schemas ============
class TrainingTaskCreate(BaseModel):
    """Create training task request"""
    name: str = Field(..., description="Task name")
    data_file_id: str = Field(..., description="Data file ID")
    config_id: str = Field(..., description="Training config ID")


class TrainingTaskResponse(BaseModel):
    """Training task response"""
    id: str
    name: str
    model_name: str
    status: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    total_steps: int
    completed_steps: int
    current_loss: Optional[float]
    best_loss: Optional[float]

    output_dir: Optional[str]
    log_file: Optional[str]

    class Config:
        from_attributes = True


class TrainingTaskUpdate(BaseModel):
    """Update training task"""
    status: Optional[str] = None
    completed_steps: Optional[int] = None
    current_loss: Optional[float] = None
    best_loss: Optional[float] = None


class TrainingMetrics(BaseModel):
    """Training metrics"""
    task_id: str
    step: int
    loss: float
    learning_rate: float
    timestamp: datetime


# ============ Data Processing Schemas ============
class DataValidationRequest(BaseModel):
    """Data validation request"""
    file_id: str = Field(..., description="Data file ID")
    format_type: str = Field(default="alpaca", description="Expected data format")


class DataValidationResponse(BaseModel):
    """Data validation response"""
    valid: bool
    total_samples: int
    issues: List[str]
    statistics: Dict[str, Any]


class DataPreviewRequest(BaseModel):
    """Data preview request"""
    file_id: str = Field(..., description="Data file ID")
    limit: int = Field(default=10, le=100, description="Number of samples to preview")


class DataPreviewResponse(BaseModel):
    """Data preview response"""
    file_id: str
    total_samples: int
    preview_count: int
    format_type: str
    samples: List[Dict[str, Any]]


# ============ Model Management Schemas ============
class ModelInfo(BaseModel):
    """Model information"""
    model_name: str
    model_size: str
    parameters: int
    max_seq_length: int
    description: str
    supported_training_methods: List[str]
    recommended: bool = False  # Whether this model is recommended


class DownloadModelRequest(BaseModel):
    """Download model request"""
    model_name: str = Field(..., description="Model name from Hugging Face")
    force_download: bool = Field(default=False, description="Force re-download")


# ============ System Schemas ============
class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str


class ApiResponse(BaseModel):
    """Generic API response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class PaginationParams(BaseModel):
    """Pagination parameters"""
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class ListResponse(BaseModel):
    """List response with pagination"""
    total: int
    skip: int
    limit: int
    items: List[Dict[str, Any]]
