"""
Training engine for Qwen3 model fine-tuning
Integrates with Transformers, PEFT, and Unsloth for efficient training
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from dataclasses import dataclass, asdict
import json
from loguru import logger

try:  # Optional heavy dependency, imported lazily when available
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
        DataCollatorForSeq2Seq,
    )
    from transformers.trainer_callback import TrainerCallback
    _TRANSFORMERS_IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - handled gracefully
    AutoModelForCausalLM = None
    AutoTokenizer = None
    TrainingArguments = None
    Trainer = None
    DataCollatorForSeq2Seq = None
    TrainerCallback = None
    _TRANSFORMERS_IMPORT_ERROR = exc

try:  # Optional dependency for LoRA fine-tuning
    from peft import get_peft_model, LoraConfig
    _PEFT_IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - handled gracefully
    get_peft_model = None
    LoraConfig = None
    _PEFT_IMPORT_ERROR = exc

if TYPE_CHECKING:  # pragma: no cover - typing only
    from datasets import Dataset
else:
    Dataset = Any

from core.model_manager import get_model_manager
from core.devices import (
    resolve_device,
    ensure_device_environment,
    coerce_torch_dtype,
    torch_device,
)

try:
    from unsloth import FastLanguageModel, is_bfloat16_supported
    HAS_UNSLOTH = True
except ImportError:
    HAS_UNSLOTH = False
    logger.warning("Unsloth not installed, training may be slower")


@dataclass
class TrainingConfig:
    """Training configuration"""
    # Model
    model_name: str = "Qwen/Qwen3-4B"
    model_type: str = "causal"  # causal or seq2seq
    device: str = "auto"
    torch_dtype: Optional[str] = None

    # Training method
    training_method: str = "lora"  # sft, lora, qlora, dpo, grpo

    # Training arguments
    output_dir: str = "./outputs"
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 4
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-4
    max_grad_norm: float = 1.0
    warmup_ratio: float = 0.1
    weight_decay: float = 0.01

    # Optimization
    optim: str = "paged_adamw_32bit"  # or adamw_torch, adamw_8bit
    lr_scheduler_type: str = "cosine"
    max_steps: int = -1

    # Data
    max_seq_length: int = 2048
    seed: int = 42

    # Model quantization
    load_in_4bit: bool = True
    load_in_8bit: bool = False

    # LoRA config
    lora_rank: int = 64
    lora_alpha: int = 128
    lora_dropout: float = 0.05
    lora_target_modules: List[str] = None

    # Logging and evaluation
    logging_steps: int = 10
    eval_steps: int = 100
    save_steps: int = 100
    evaluation_strategy: str = "no"
    save_strategy: str = "steps"
    save_total_limit: int = 3

    # Hardware
    use_flash_attention: bool = True
    gradient_checkpointing: bool = True
    fp16: bool = False
    bf16: bool = True

    def __post_init__(self):
        """Post-initialization hook"""
        if self.lora_target_modules is None:
            self.lora_target_modules = ["q_proj", "v_proj"]
        if not self.device:
            self.device = "auto"

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "TrainingConfig":
        """Create config from dictionary"""
        return cls(**{k: v for k, v in config_dict.items() if k in cls.__dataclass_fields__})

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class Trainer_Qwen3:
    """Qwen3 Fine-tuning Trainer"""

    def __init__(self, config: TrainingConfig):
        """Initialize trainer"""
        self.config = config
        self.model = None
        self.tokenizer = None
        self.trainer = None
        self.device = resolve_device(self.config.device)
        ensure_device_environment(self.device)
        self.config.device = self.device
        self._adjust_config_for_device()
        self.resolved_dtype = coerce_torch_dtype(
            self.device,
            explicit=self.config.torch_dtype,
            prefer_bf16=self.config.bf16,
            prefer_fp16=self.config.fp16 or self.device == "mps",
        )
        if self.resolved_dtype is not None and not self.config.torch_dtype:
            # Persist human readable dtype for downstream reporting
            self.config.torch_dtype = str(self.resolved_dtype).split(".")[-1]
        if self.resolved_dtype is None and self.config.torch_dtype:
            # Remove stale dtype hint when resolution failed
            self.config.torch_dtype = None
        self.torch_device = torch_device(self.device)
        dtype_repr = (
            str(self.resolved_dtype).replace("torch.", "")
            if self.resolved_dtype is not None
            else "float32"
        )
        logger.info(
            "Initialized Trainer for {} using device={} (dtype={})",
            config.model_name,
            self.device,
            dtype_repr,
        )

    @staticmethod
    def _ensure_transformers_available():
        """Ensure transformers is installed before executing transformer-specific logic."""
        if AutoModelForCausalLM is None or AutoTokenizer is None:
            raise ImportError(
                "transformers is required for training operations. Install it with 'pip install transformers'."
            ) from _TRANSFORMERS_IMPORT_ERROR

    def load_model_and_tokenizer(self):
        """Load model and tokenizer"""
        self._ensure_transformers_available()
        logger.info(f"Loading model: {self.config.model_name}")

        # Use Unsloth if available and not using quantization
        if (
            HAS_UNSLOTH
            and self.config.training_method in ["lora", "qlora"]
            and self.device != "mps"
        ):
            logger.info("Using Unsloth for faster training")
            self.model, self.tokenizer = self._load_model_with_unsloth()
        else:
            logger.info("Using standard Transformers loading")
            self.model, self.tokenizer = self._load_model_standard()

    def _load_model_with_unsloth(self) -> tuple:
        """Load model using Unsloth"""
        max_seq_length = self.config.max_seq_length
        load_in_4bit = self.config.load_in_4bit

        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=self.config.model_name,
            max_seq_length=max_seq_length,
            dtype=self.resolved_dtype,
            load_in_4bit=load_in_4bit,
            token=os.getenv("HF_TOKEN"),
        )

        # Add LoRA if configured
        if self.config.training_method == "lora":
            model = FastLanguageModel.get_peft_model(
                model,
                r=self.config.lora_rank,
                lora_alpha=self.config.lora_alpha,
                lora_dropout=self.config.lora_dropout,
                bias="none",
                use_gradient_checkpointing="unsloth",
                use_rslora=True,
            )

        # Set up for inference
        FastLanguageModel.for_inference(model)

        return model, tokenizer

    def _load_model_standard(self) -> tuple:
        """Load model using standard Transformers"""
        self._ensure_transformers_available()
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_name,
            trust_remote_code=True,
            token=os.getenv("HF_TOKEN"),
        )

        # Set pad token
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # Load model with quantization if needed
        quantization_config = None
        if self.config.load_in_4bit:
            from transformers import BitsAndBytesConfig
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype="float16",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )

        device_map: Optional[str] = "auto" if self.device == "cuda" else None
        model = AutoModelForCausalLM.from_pretrained(
            self.config.model_name,
            quantization_config=quantization_config,
            device_map=device_map,
            torch_dtype=self.resolved_dtype,
            trust_remote_code=True,
            token=os.getenv("HF_TOKEN"),
        )

        if device_map is None:
            model.to(self.torch_device)
        elif self.device.startswith("cuda"):
            model.to(self.torch_device)

        # Add LoRA
        if self.config.training_method == "lora":
            if LoraConfig is None or get_peft_model is None:
                raise ImportError(
                    "peft is required for LoRA training. Install it with 'pip install peft'."
                ) from _PEFT_IMPORT_ERROR
            lora_config = LoraConfig(
                r=self.config.lora_rank,
                lora_alpha=self.config.lora_alpha,
                lora_dropout=self.config.lora_dropout,
                bias="none",
                task_type="CAUSAL_LM",
                target_modules=self.config.lora_target_modules,
            )
            model = get_peft_model(model, lora_config)

        return model, tokenizer

    def prepare_dataset(self, dataset: Dataset) -> Dataset:
        """Prepare dataset for training"""
        logger.info("Preparing dataset for training")

        def tokenize_function(examples):
            """Tokenize function for Alpaca format"""
            if "instruction" in examples:
                # Alpaca format
                texts = []
                for inst, inp, out in zip(
                    examples.get("instruction", []),
                    examples.get("input", []),
                    examples.get("output", []),
                ):
                    if inp:
                        text = f"{inst}\n{inp}\n{out}"
                    else:
                        text = f"{inst}\n{out}"
                    texts.append(text)

                tokenized = self.tokenizer(
                    texts,
                    max_length=self.config.max_seq_length,
                    truncation=True,
                    padding=False,
                )
            else:
                # Text format
                tokenized = self.tokenizer(
                    examples["text"],
                    max_length=self.config.max_seq_length,
                    truncation=True,
                    padding=False,
                )

            tokenized["labels"] = tokenized["input_ids"].copy()
            return tokenized

        dataset = dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=dataset.column_names,
            desc="Tokenizing",
        )

        return dataset

    def train(
        self,
        train_dataset: Dataset,
        eval_dataset: Optional[Dataset] = None,
        callbacks: Optional[List[Any]] = None,
    ):
        """Start training"""
        self._ensure_transformers_available()
        logger.info("Starting training")

        # Prepare dataset
        train_dataset = self.prepare_dataset(train_dataset)

        # Create training arguments
        training_args = TrainingArguments(
            output_dir=self.config.output_dir,
            num_train_epochs=self.config.num_train_epochs,
            per_device_train_batch_size=self.config.per_device_train_batch_size,
            per_device_eval_batch_size=self.config.per_device_eval_batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            learning_rate=self.config.learning_rate,
            max_grad_norm=self.config.max_grad_norm,
            warmup_ratio=self.config.warmup_ratio,
            weight_decay=self.config.weight_decay,
            optim=self.config.optim,
            lr_scheduler_type=self.config.lr_scheduler_type,
            max_steps=self.config.max_steps,
            logging_steps=self.config.logging_steps,
            save_steps=self.config.save_steps,
            save_strategy=self.config.save_strategy,
            save_total_limit=self.config.save_total_limit,
            evaluation_strategy=self.config.evaluation_strategy,
            eval_steps=self.config.eval_steps if eval_dataset else None,
            fp16=self.config.fp16 and self.device in ("cuda", "mps"),
            bf16=self.config.bf16 and self.device.startswith("cuda"),
            gradient_checkpointing=self.config.gradient_checkpointing,
            report_to=["tensorboard"],
            push_to_hub=False,
        )

        # Create trainer
        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=DataCollatorForSeq2Seq(
                self.tokenizer,
                pad_to_multiple_of=8,
                return_tensors="pt",
                padding=True,
            ),
            callbacks=callbacks,
        )

        # Start training
        self.trainer.train()

        logger.info("Training completed")

    def save_model(self, output_dir: str):
        """Save model and tokenizer"""
        self._ensure_transformers_available()
        logger.info(f"Saving model to {output_dir}")
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)

        # Save config
        with open(Path(output_dir) / "training_config.json", "w") as f:
            json.dump(self.config.to_dict(), f, indent=2)

        logger.info("Model saved successfully")

    def load_model(self, model_path: str):
        """Load fine-tuned model"""
        logger.info(f"Loading model from {model_path}")
        self.model = AutoModelForCausalLM.from_pretrained(model_path)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        logger.info("Model loaded successfully")

    def _adjust_config_for_device(self) -> None:
        """Tweak configuration knobs based on the resolved device."""
        if self.device != "cuda" and self.config.load_in_4bit:
            logger.warning(
                "4-bit quantization is only supported on CUDA. Disabling for device {}.",
                self.device,
            )
            self.config.load_in_4bit = False

        if self.device == "mps":
            if self.config.bf16:
                logger.warning("bfloat16 is not supported on MPS; falling back to fp16.")
                self.config.bf16 = False
            if not self.config.fp16:
                logger.info("Enabling fp16 to match MPS hardware constraints.")
                self.config.fp16 = True
            if self.config.torch_dtype and self.config.torch_dtype.lower() != "float16":
                logger.info("Overriding torch_dtype to float16 for MPS compatibility.")
                self.config.torch_dtype = "float16"

        if self.device == "cpu" and self.config.fp16:
            logger.warning("fp16 is not supported on CPU; reverting to full precision.")
            self.config.fp16 = False
        if self.device == "cpu" and self.config.torch_dtype:
            dtype_lower = self.config.torch_dtype.lower()
            if dtype_lower in {"float16", "bfloat16"}:
                logger.warning(
                    "Half-precision dtype '%s' is not supported on CPU; clearing override.",
                    self.config.torch_dtype,
                )
                self.config.torch_dtype = None
