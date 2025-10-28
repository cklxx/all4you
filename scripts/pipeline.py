#!/usr/bin/env python3
"""One-click pipeline for data processing, fine-tuning, and evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

import yaml
from loguru import logger

from backend.core.data_processor import DataProcessor, validate_data_format
from backend.core.dataset_hub import ModelScopeDatasetManager
from backend.core.evaluator import AutoEvaluator
from backend.core.trainer import Trainer_Qwen3, TrainingConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the full Qwen fine-tuning pipeline: data processing, training, and evaluation."
        )
    )
    parser.add_argument(
        "--data",
        default=None,
        help="Path to the training dataset (JSON/JSONL/CSV/TXT).",
    )
    parser.add_argument(
        "--data-format",
        default="alpaca",
        choices=DataProcessor.SUPPORTED_STRUCTURES,
        help="Structure of the dataset after processing.",
    )
    parser.add_argument(
        "--data-type",
        default=None,
        choices=DataProcessor.SUPPORTED_FORMATS,
        help="Optional explicit source file type (auto-detected by default).",
    )
    parser.add_argument(
        "--eval-data",
        default=None,
        help="Optional path to a separate evaluation dataset.",
    )
    parser.add_argument(
        "--eval-ratio",
        type=float,
        default=0.0,
        help=(
            "When no eval dataset is provided, reserve this ratio (0-0.5) of the training data for evaluation."
        ),
    )
    parser.add_argument(
        "--config",
        default="backend/configs/default.yaml",
        help="Training configuration YAML file.",
    )
    parser.add_argument(
        "--output-dir",
        default="backend/outputs/pipeline-run",
        help="Directory where fine-tuned artifacts will be stored.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the base model name defined in the training config.",
    )
    parser.add_argument(
        "--judge-model",
        default="Qwen/Qwen3-7B",
        help=(
            "Model used for automatic evaluation. Set to 'none' to disable model-based judging."
        ),
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=512,
        help="Maximum new tokens to generate during evaluation.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature for evaluation generations.",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=0.9,
        help="Top-p nucleus sampling value for evaluation generations.",
    )
    parser.add_argument(
        "--no-judge",
        action="store_true",
        help="Disable model-based automatic evaluation and only generate predictions.",
    )
    parser.add_argument(
        "--moda-dataset",
        default=None,
        help=(
            "ModelScope (魔搭) dataset preset name or dataset_id to download automatically."
        ),
    )
    parser.add_argument(
        "--moda-split",
        default=None,
        help="Optional dataset split override when using ModelScope.",
    )
    parser.add_argument(
        "--moda-subset",
        default=None,
        help="Optional subset name when using ModelScope datasets.",
    )
    parser.add_argument(
        "--moda-fields",
        default=None,
        help=(
            "Comma separated field mapping for ModelScope datasets, e.g. "
            "instruction=query,input=context,output=answer."
        ),
    )
    parser.add_argument(
        "--moda-limit",
        type=int,
        default=None,
        help="Limit the number of samples downloaded from ModelScope.",
    )
    parser.add_argument(
        "--moda-cache-dir",
        default="datasets/modelscope",
        help="Cache directory for ModelScope datasets.",
    )
    return parser.parse_args()


def ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_field_mapping(mapping: Optional[str]) -> Dict[str, str]:
    if not mapping:
        return {}
    result: Dict[str, str] = {}
    for raw_pair in mapping.split(","):
        pair = raw_pair.strip()
        if not pair:
            continue
        if "=" not in pair:
            raise ValueError(f"Invalid field mapping entry: '{pair}'")
        key, value = pair.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def split_train_eval(
    data: List[Dict[str, Any]], ratio: float
) -> tuple[List[Dict[str, Any]], Optional[List[Dict[str, Any]]]]:
    if ratio <= 0:
        return data, None

    ratio = min(ratio, 0.5)
    split_idx = int(len(data) * ratio)
    if split_idx == 0:
        return data, None

    eval_subset = data[:split_idx]
    train_subset = data[split_idx:]
    return train_subset, eval_subset


def process_dataset(
    path: str,
    format_type: str,
    file_type: Optional[str],
    save_dir: Path,
    prefix: str,
) -> Dict[str, Any]:
    logger.info("Processing dataset: {}", path)
    records = DataProcessor.load_and_format_data(path, format_type=format_type, file_type=file_type)
    validation = validate_data_format(records, format_type=format_type)
    if not validation["valid"]:
        logger.warning("Dataset validation reported issues: {}", validation["issues"])

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    processed_path = save_dir / f"{prefix}_{timestamp}.json"
    ensure_output_dir(processed_path.parent)
    save_json(processed_path, {"records": records, "validation": validation})
    logger.info("Saved processed dataset snapshot to {}", processed_path)

    dataset = DataProcessor.create_huggingface_dataset(records, format_type=format_type)
    return {
        "records": records,
        "validation": validation,
        "dataset": dataset,
        "snapshot": str(processed_path),
    }


def load_training_config(path: str, overrides: Dict[str, Any]) -> TrainingConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Training config not found: {path}")

    config_dict = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config_dict.update({k: v for k, v in overrides.items() if v is not None})
    return TrainingConfig.from_dict(config_dict)



def main() -> int:
    args = parse_args()
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    dataset_info: Optional[Dict[str, Any]] = None

    field_mapping: Dict[str, str] = {}
    try:
        field_mapping = parse_field_mapping(args.moda_fields)
    except ValueError as exc:
        logger.error(str(exc))
        return 1

    if args.moda_dataset:
        manager = ModelScopeDatasetManager(cache_dir=args.moda_cache_dir)
        try:
            dataset_info = manager.prepare_for_training(
                name_or_id=args.moda_dataset,
                split=args.moda_split,
                subset=args.moda_subset,
                fields=field_mapping or None,
                limit=args.moda_limit,
            )
        except Exception as exc:  # pragma: no cover - external dependency call
            logger.error("Failed to download ModelScope dataset: {}", exc)
            return 1
        if not dataset_info["data_path"]:
            logger.error("ModelScope dataset download did not produce a usable file.")
            return 1
        data_path = Path(dataset_info["data_path"])
        logger.info("Using ModelScope dataset located at %s", data_path)
    else:
        if not args.data:
            logger.error("Either --data or --moda-dataset must be provided.")
            return 1
        data_path = Path(args.data)

    if not data_path.exists():
        logger.error("Training data file not found: {}", data_path)
        return 1

    output_dir = Path(args.output_dir)
    ensure_output_dir(output_dir)

    training_info = process_dataset(
        path=str(data_path),
        format_type=args.data_format,
        file_type=args.data_type,
        save_dir=output_dir / "processed",
        prefix="train",
    )

    train_records = training_info["records"]
    eval_records: Optional[List[Dict[str, Any]]] = None
    eval_dataset = None

    if args.eval_data:
        eval_path = Path(args.eval_data)
        if not eval_path.exists():
            logger.error("Evaluation data file not found: {}", eval_path)
            return 1
        eval_info = process_dataset(
            path=str(eval_path),
            format_type=args.data_format,
            file_type=args.data_type,
            save_dir=output_dir / "processed",
            prefix="eval",
        )
        eval_records = eval_info["records"]
        eval_dataset = eval_info["dataset"]
    else:
        train_records, eval_records = split_train_eval(train_records, args.eval_ratio)
        if eval_records:
            eval_dataset = DataProcessor.create_huggingface_dataset(eval_records, format_type=args.data_format)
            training_info["dataset"] = DataProcessor.create_huggingface_dataset(
                train_records, format_type=args.data_format
            )
        training_info["records"] = train_records

    train_dataset = training_info["dataset"]
    if len(train_dataset) == 0:
        logger.error("No samples available for training after preprocessing.")
        return 1

    overrides = {"output_dir": str(output_dir)}
    if args.model:
        overrides["model_name"] = args.model

    training_config = load_training_config(args.config, overrides)

    trainer = Trainer_Qwen3(training_config)
    trainer.load_model_and_tokenizer()
    trainer.train(train_dataset=train_dataset, eval_dataset=eval_dataset)
    trainer.save_model(str(output_dir))

    eval_report = None
    judge_model = None if args.no_judge or args.judge_model.lower() == "none" else args.judge_model

    if eval_records:
        evaluator = AutoEvaluator(
            model_path=str(output_dir),
            judge_model_name=judge_model,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
        )
        eval_report = evaluator.evaluate(
            samples=eval_records,
            format_type=args.data_format,
            use_judge=bool(judge_model),
        )
        save_json(output_dir / "evaluation_report.json", eval_report)
        logger.info("Saved evaluation report to {}", output_dir / "evaluation_report.json")
    else:
        logger.warning("No evaluation data provided; skipping automatic evaluation.")

    pipeline_summary = {
        "training_data": {
            "path": str(data_path),
            "processed_snapshot": training_info["snapshot"],
            "num_samples": len(train_records),
        },
        "modelscope": None,
        "evaluation_data": {
            "path": str(args.eval_data) if args.eval_data else None,
            "num_samples": len(eval_records) if eval_records else 0,
            "used_judge_model": bool(judge_model),
        },
        "training": {
            "config": training_config.to_dict(),
            "output_dir": str(output_dir),
        },
        "evaluation": eval_report,
    }

    if dataset_info:
        pipeline_summary["modelscope"] = {
            "requested": args.moda_dataset,
            "dataset_id": dataset_info["config"].dataset_id,
            "split": dataset_info["config"].split,
            "subset": dataset_info["config"].subset,
            "raw_path": dataset_info["raw_path"],
            "formatted_path": dataset_info.get("formatted_path"),
            "field_mapping": dataset_info["config"].fields,
            "limit": args.moda_limit,
        }
    else:
        pipeline_summary.pop("modelscope")
    save_json(output_dir / "pipeline_summary.json", pipeline_summary)
    logger.info(
        "Pipeline completed successfully. Summary saved to {}", output_dir / "pipeline_summary.json"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
