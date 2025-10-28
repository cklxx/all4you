#!/usr/bin/env python3
"""One-click pipeline for data processing, fine-tuning, and evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from loguru import logger

from backend.core.data_processor import DataProcessor, validate_data_format
from backend.core.dataset_hub import ModelScopeDatasetManager
from backend.core.evaluator import AutoEvaluator, OllamaJudgeUnavailable
from backend.core.trainer import Trainer_Qwen3, TrainingConfig
from backend.core.devices import DEVICE_CHOICES


SECTION_DIVIDER = "=" * 80
SUBSECTION_DIVIDER = "-" * 80


PIPELINE_PRESETS: Dict[str, Dict[str, Any]] = {
    "alpaca-zh-lora": {
        "description": (
            "下载魔搭中文 Alpaca 数据集，并在 Qwen/Qwen3-0.6B 上使用 LoRA 进行一键微调，"
            "默认以 MPS 设备快速验证，并优先调用 Ollama 8B 评测模型，缺失时回退至 0.6B。"
        ),
        "config": "backend/configs/qwen3-0.6b-mps.yaml",
        "device": "mps",
        "model": "Qwen/Qwen3-0.6B",
        "judge_model": "ollama:qwen2:8b",
        "fallback_judge_model": "Qwen/Qwen3-0.6B",
        "moda_dataset": "alpaca_zh",
        "output_dir": "backend/outputs/alpaca-zh-lora",
        "data_format": "alpaca",
        "eval_ratio": 0.1,
    },
    # 保留旧名称作为别名
    "search-intent-lora": {
        "description": "(已更新) 使用中文 Alpaca 数据集进行 LoRA 微调",
        "config": "backend/configs/qwen3-0.6b-mps.yaml",
        "device": "mps",
        "model": "Qwen/Qwen3-0.6B",
        "judge_model": "ollama:qwen2:8b",
        "fallback_judge_model": "Qwen/Qwen3-0.6B",
        "moda_dataset": "alpaca_zh",
        "output_dir": "backend/outputs/alpaca-zh-lora",
        "data_format": "alpaca",
        "eval_ratio": 0.1,
    },
}


class PipelineProgress:
    """Simple progress tracker that emits stage updates to the logger."""

    STATUS_SYMBOLS = {
        "pending": "…",
        "running": "▶",
        "completed": "✓",
        "failed": "✗",
    }

    def __init__(self, stages: List[str]):
        self._stages = stages
        self._status = {name: "pending" for name in stages}
        self._current: Optional[str] = None
        self._render(initial=True)

    def start(self, stage: str) -> None:
        self._set_status(stage, "running")
        self._current = stage

    def complete(self, stage: str) -> None:
        self._set_status(stage, "completed", render=False)
        # 显示完成状态
        idx = self._stages.index(stage) + 1
        total = len(self._stages)
        completed = sum(1 for s in self._status.values() if s == "completed")
        logger.info(f"进度 {completed}/{total} - [{idx:02d}] ✓ {stage}")
        if self._current == stage:
            self._current = None

    def fail(self, stage: str) -> None:
        self._set_status(stage, "failed", render=False)
        # 显示失败状态
        idx = self._stages.index(stage) + 1
        total = len(self._stages)
        completed = sum(1 for s in self._status.values() if s == "completed")
        logger.error(f"进度 {completed}/{total} - [{idx:02d}] ✗ {stage}")
        if self._current == stage:
            self._current = None

    def _set_status(self, stage: str, status: str, render: bool = True) -> None:
        if stage not in self._status:
            raise ValueError(f"Unknown stage '{stage}'")
        self._status[stage] = status
        if render:
            self._render()

    def _render(self, *, initial: bool = False) -> None:
        total = len(self._stages)
        completed = sum(1 for status in self._status.values() if status == "completed")

        if initial:
            # 初始化时显示完整列表
            header = f"进度 {completed}/{total}"
            lines = [header]
            for idx, stage in enumerate(self._stages, start=1):
                status = self._status[stage]
                symbol = self.STATUS_SYMBOLS.get(status, "?")
                lines.append(f"  [{idx:02d}] {symbol} {stage}")
            message = "\n".join(lines)
            logger.info("\n{}\n{}", SECTION_DIVIDER, message)
        else:
            # 状态更新时只显示当前阶段
            if self._current:
                idx = self._stages.index(self._current) + 1
                status = self._status[self._current]
                symbol = self.STATUS_SYMBOLS.get(status, "?")
                logger.info(f"进度 {completed}/{total} - [{idx:02d}] {symbol} {self._current}")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    if argv is None:
        argv = sys.argv[1:]

    preset_choices = sorted(PIPELINE_PRESETS.keys())
    preset_help = ""
    if preset_choices:
        preset_help = " 可选预设: " + "; ".join(
            f"{name}（{PIPELINE_PRESETS[name]['description']}）" for name in preset_choices
        )

    parser = argparse.ArgumentParser(
        description=(
            "Run the full Qwen fine-tuning pipeline: data processing, training, and evaluation."
        )
    )
    if preset_choices:
        parser.add_argument(
            "--preset",
            choices=preset_choices,
            help="使用预设组合快速运行常见场景。" + preset_help,
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
        "--device",
        default="auto",
        choices=DEVICE_CHOICES,
        help="Preferred device for fine-tuning (auto, cuda, mps, cpu).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the base model name defined in the training config.",
    )
    parser.add_argument(
        "--judge-model",
        default="Qwen/Qwen3-4B",
        help=(
            "Model used for automatic evaluation. Defaults to Qwen/Qwen3-4B; "
            "set to 'none' to disable or switch to Qwen/Qwen3-0.6B for rapid validation."
        ),
    )
    parser.add_argument(
        "--judge-device",
        default="inherit",
        choices=DEVICE_CHOICES + ("inherit",),
        help=(
            "Preferred device for the judge model. Use 'inherit' (default) to reuse --device."
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
        "--fallback-judge-model",
        default=None,
        help=(
            "Alternative judge model used when the primary judge is unavailable."
        ),
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
    defaults = {
        action.dest: action.default
        for action in parser._actions
        if action.dest not in {"help"}
    }
    args = parser.parse_args(argv)

    if getattr(args, "preset", None):
        preset = PIPELINE_PRESETS[args.preset]
        for key, value in preset.items():
            if key == "description":
                continue
            default_value = defaults.get(key)
            if getattr(args, key, default_value) == default_value:
                setattr(args, key, value)

    return args


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



def log_section(title: str) -> None:
    logger.info("\n{}\n{}\n{}", SECTION_DIVIDER, title, SECTION_DIVIDER)


def log_subsection(title: str) -> None:
    logger.info("\n{}\n{}\n{}", SUBSECTION_DIVIDER, title, SUBSECTION_DIVIDER)


def main() -> int:
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    progress = PipelineProgress(
        [
            "解析参数",
            "准备数据集",
            "数据预处理",
            "模型训练",
            "自动评测",
            "结果汇总",
        ]
    )

    progress.start("解析参数")
    log_section("解析参数")
    args = parse_args()

    if args.preset:
        logger.info("Using pipeline preset '%s'", args.preset)

    field_mapping: Dict[str, str] = {}
    try:
        field_mapping = parse_field_mapping(args.moda_fields)
    except ValueError as exc:
        progress.fail("解析参数")
        logger.error(str(exc))
        return 1
    progress.complete("解析参数")

    dataset_info: Optional[Dict[str, Any]] = None

    progress.start("准备数据集")
    log_section("准备数据集")
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
            progress.fail("准备数据集")
            logger.error("Failed to download ModelScope dataset: {}", exc)
            return 1
        if not dataset_info["data_path"]:
            progress.fail("准备数据集")
            logger.error("ModelScope dataset download did not produce a usable file.")
            return 1
        data_path = Path(dataset_info["data_path"])
        logger.info("Using ModelScope dataset located at %s", data_path)
    else:
        if not args.data:
            progress.fail("准备数据集")
            logger.error("Either --data or --moda-dataset must be provided.")
            return 1
        data_path = Path(args.data)

    if not data_path.exists():
        progress.fail("准备数据集")
        logger.error("Training data file not found: {}", data_path)
        return 1
    progress.complete("准备数据集")

    output_dir = Path(args.output_dir)
    ensure_output_dir(output_dir)

    progress.start("数据预处理")
    log_section("数据预处理")
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
            progress.fail("数据预处理")
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
        log_subsection("拆分训练与评估集")
        train_records, eval_records = split_train_eval(train_records, args.eval_ratio)
        if eval_records:
            eval_dataset = DataProcessor.create_huggingface_dataset(eval_records, format_type=args.data_format)
            training_info["dataset"] = DataProcessor.create_huggingface_dataset(
                train_records, format_type=args.data_format
            )
        training_info["records"] = train_records

    train_dataset = training_info["dataset"]
    if len(train_dataset) == 0:
        progress.fail("数据预处理")
        logger.error("No samples available for training after preprocessing.")
        return 1
    progress.complete("数据预处理")

    overrides = {"output_dir": str(output_dir), "device": args.device}
    if args.model:
        overrides["model_name"] = args.model

    log_section("加载与训练模型")
    progress.start("模型训练")
    training_config = load_training_config(args.config, overrides)

    if args.device == "mps" and not args.model and training_config.model_name != "Qwen/Qwen3-0.6B":
        logger.info(
            "MPS device requested without explicit model override; switching base model to Qwen/Qwen3-0.6B for best compatibility."
        )
        training_config.model_name = "Qwen/Qwen3-0.6B"

    try:
        trainer = Trainer_Qwen3(training_config)
        trainer.load_model_and_tokenizer()
        trainer.train(train_dataset=train_dataset, eval_dataset=eval_dataset)
        trainer.save_model(str(output_dir))
    except Exception:  # pragma: no cover - runtime failure surfaced to user
        progress.fail("模型训练")
        logger.exception("模型训练阶段出现异常，请检查上述日志。")
        return 1
    progress.complete("模型训练")

    eval_report = None

    def _normalize_judge(name: Optional[str]) -> Optional[str]:
        if not name:
            return None
        lowered = name.lower()
        if lowered == "none":
            return None
        return name

    requested_judge_model = None if args.no_judge else _normalize_judge(args.judge_model)
    fallback_judge_model = _normalize_judge(getattr(args, "fallback_judge_model", None))
    active_judge_model: Optional[str] = requested_judge_model

    judge_device = args.judge_device
    if judge_device == "inherit":
        judge_device = args.device

    progress.start("自动评测")
    log_section("自动评测")
    if eval_records:
        try:
            def run_evaluation(judge_name: Optional[str]) -> Dict[str, Any]:
                evaluator = AutoEvaluator(
                    model_path=str(output_dir),
                    judge_model_name=judge_name,
                    max_new_tokens=args.max_new_tokens,
                    temperature=args.temperature,
                    top_p=args.top_p,
                    device=training_config.device,
                    judge_device=judge_device,
                )
                report = evaluator.evaluate(
                    samples=eval_records,
                    format_type=args.data_format,
                    use_judge=bool(judge_name),
                )
                return report

            try:
                eval_report = run_evaluation(active_judge_model)
            except OllamaJudgeUnavailable as exc:
                logger.warning(
                    "Ollama 评测模型不可用（{}）。", exc
                )
                if fallback_judge_model:
                    logger.info(
                        "回退至评测模型 {}", fallback_judge_model
                    )
                    active_judge_model = fallback_judge_model
                    eval_report = run_evaluation(active_judge_model)
                else:
                    logger.info("未配置回退评测模型，将仅生成预测结果。")
                    active_judge_model = None
                    eval_report = run_evaluation(None)

            if eval_report is not None:
                resolved_judge = eval_report.get("judge_model")
                if resolved_judge is not None or active_judge_model is None:
                    active_judge_model = resolved_judge
                if active_judge_model is not None:
                    eval_report.setdefault("active_judge_model", active_judge_model)
                if fallback_judge_model:
                    eval_report.setdefault("fallback_judge_model", fallback_judge_model)
                if requested_judge_model:
                    eval_report.setdefault("requested_judge_model", requested_judge_model)

            save_json(output_dir / "evaluation_report.json", eval_report)
            logger.info("Saved evaluation report to {}", output_dir / "evaluation_report.json")
        except Exception:  # pragma: no cover - runtime failure surfaced to user
            progress.fail("自动评测")
            logger.exception("自动评测阶段出现异常，请检查上述日志。")
            return 1
        progress.complete("自动评测")
    else:
        logger.warning("No evaluation data provided; skipping automatic evaluation.")
        active_judge_model = None
        progress.complete("自动评测")

    progress.start("结果汇总")
    log_section("结果汇总")
    try:
        pipeline_summary = {
            "preset": args.preset,
            "training_data": {
                "path": str(data_path),
                "processed_snapshot": training_info["snapshot"],
                "num_samples": len(train_records),
            },
            "modelscope": None,
            "evaluation_data": {
                "path": str(args.eval_data) if args.eval_data else None,
                "num_samples": len(eval_records) if eval_records else 0,
                "used_judge_model": bool(active_judge_model),
                "requested_judge_model": requested_judge_model,
                "active_judge_model": active_judge_model,
                "fallback_judge_model": fallback_judge_model,
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
    except Exception:  # pragma: no cover - runtime failure surfaced to user
        progress.fail("结果汇总")
        logger.exception("结果汇总阶段出现异常，请检查上述日志。")
        return 1
    progress.complete("结果汇总")
    return 0


if __name__ == "__main__":
    sys.exit(main())
