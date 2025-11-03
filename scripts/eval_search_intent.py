#!/usr/bin/env python3
"""Evaluate a search-intent SFT checkpoint with one command."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger

from backend.core.data_processor import DataProcessor
from backend.core.dataset_hub import prepare_huggingface_dataset
from backend.core.evaluator import AutoEvaluator, OllamaJudgeUnavailable


DEFAULT_FIELDS = (
    "instruction=请判断以下医疗搜索查询的意图类别并输出类别名称。查询：{query},"
    "input=,output={label}"
)


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


def infer_file_type(path: Path) -> Optional[str]:
    suffix = path.suffix.lower().lstrip(".")
    return suffix or None


def prepare_records_from_file(
    data_path: Path,
    *,
    format_type: str,
    file_type: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], str]:
    records = DataProcessor.load_and_format_data(
        str(data_path), format_type=format_type, file_type=file_type
    )
    return records, format_type


def prepare_records_from_hf(
    dataset_id: str,
    *,
    split: str,
    fields: Dict[str, str],
    limit: Optional[int],
    cache_dir: Optional[Path],
) -> Tuple[List[Dict[str, Any]], str, Path]:
    info = prepare_huggingface_dataset(
        dataset_id=dataset_id,
        split=split,
        fields=fields or None,
        limit=limit,
        cache_dir=cache_dir,
    )
    records = info["formatted_records"] or info["raw_records"]
    format_type = "alpaca" if info["formatted_records"] else "raw"
    resolved_path = Path(info["data_path"])
    return records, format_type, resolved_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Quickly evaluate a search-intent SFT checkpoint."
    )
    parser.add_argument(
        "--model-dir",
        default="backend/outputs/search-intent-lora",
        help="Path to the fine-tuned checkpoint directory.",
    )
    parser.add_argument(
        "--eval-data",
        default=None,
        help="Optional evaluation file (JSON/JSONL/CSV/TXT). "
        "When omitted the script pulls wyp/CBlue-KUAKE-QIC automatically.",
    )
    parser.add_argument(
        "--eval-format",
        default="alpaca",
        choices=("alpaca", "sharegpt", "raw"),
        help="Expected format of --eval-data.",
    )
    parser.add_argument(
        "--eval-file-type",
        default=None,
        help="Explicit file type for --eval-data (json/jsonl/csv/txt). "
        "Auto-inferred when omitted.",
    )
    parser.add_argument(
        "--hf-dataset",
        default="wyp/CBlue-KUAKE-QIC",
        help="Hugging Face dataset to download when --eval-data is not provided.",
    )
    parser.add_argument(
        "--hf-split",
        default="validation",
        help="Dataset split to use for the Hugging Face dataset.",
    )
    parser.add_argument(
        "--hf-fields",
        default=DEFAULT_FIELDS,
        help="Field mapping (k=v,...) applied to the Hugging Face dataset.",
    )
    parser.add_argument(
        "--hf-limit",
        type=int,
        default=None,
        help="Optional limit when sampling from the Hugging Face dataset.",
    )
    parser.add_argument(
        "--hf-cache-dir",
        default=None,
        help="Custom cache directory for downloaded Hugging Face data.",
    )
    parser.add_argument(
        "--device",
        default="mps",
        help="Device for the fine-tuned model (auto/cuda/mps/cpu).",
    )
    parser.add_argument(
        "--judge-model",
        default="ollama:qwen3:8b",
        help="Judge model name. Use 'none' to disable automatic scoring.",
    )
    parser.add_argument(
        "--judge-device",
        default="inherit",
        help="Device for the judge model. 'inherit' reuses --device.",
    )
    parser.add_argument(
        "--no-judge",
        action="store_true",
        help="Disable automatic judging and only generate predictions.",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=256,
        help="Maximum new tokens for each prediction.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Generation temperature for the fine-tuned model.",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=1.0,
        help="Top-p nucleus sampling parameter.",
    )
    parser.add_argument(
        "--report-path",
        default=None,
        help="Where to save the evaluation report JSON. Defaults to "
        "<model-dir>/search_intent_eval_report.json.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print individual sample scores in addition to the summary.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    model_dir = Path(args.model_dir).expanduser().resolve()
    if not model_dir.exists():
        logger.error("Model directory not found: {}", model_dir)
        return 1

    judge_model = args.judge_model
    if args.no_judge or (judge_model and judge_model.lower() == "none"):
        judge_model = None

    records: List[Dict[str, Any]]
    format_type: str
    source_hint: Optional[Path] = None

    if args.eval_data:
        data_path = Path(args.eval_data).expanduser().resolve()
        if not data_path.exists():
            logger.error("Evaluation data file not found: {}", data_path)
            return 1
        file_type = args.eval_file_type or infer_file_type(data_path)
        logger.info("Loading evaluation data from {}", data_path)
        records, format_type = prepare_records_from_file(
            data_path, format_type=args.eval_format, file_type=file_type
        )
        source_hint = data_path
    else:
        try:
            field_mapping = parse_field_mapping(args.hf_fields)
        except ValueError as exc:
            logger.error("Failed to parse --hf-fields: {}", exc)
            return 1
        cache_dir = Path(args.hf_cache_dir).expanduser().resolve() if args.hf_cache_dir else None
        logger.info(
            "Downloading evaluation split '{}' from {}",
            args.hf_split,
            args.hf_dataset,
        )
        records, format_type, source_hint = prepare_records_from_hf(
            args.hf_dataset,
            split=args.hf_split,
            fields=field_mapping,
            limit=args.hf_limit,
            cache_dir=cache_dir,
        )

    if not records:
        logger.error("No evaluation samples available.")
        return 1

    report_path = (
        Path(args.report_path).expanduser().resolve()
        if args.report_path
        else model_dir / "search_intent_eval_report.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)

    evaluator = AutoEvaluator(
        model_path=str(model_dir),
        judge_model_name=judge_model,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        top_p=args.top_p,
        device=args.device,
        judge_device=args.judge_device,
    )

    logger.info(
        "Running evaluation on %d samples%s",
        len(records),
        f" from {source_hint}" if source_hint else "",
    )

    try:
        report = evaluator.evaluate(
            samples=records,
            format_type=format_type,
            use_judge=judge_model is not None,
        )
    except OllamaJudgeUnavailable as exc:
        logger.warning("Judge model unavailable: {}", exc)
        logger.info("Retrying without automatic judging.")
        report = evaluator.evaluate(
            samples=records,
            format_type=format_type,
            use_judge=False,
        )

    report["source"] = str(source_hint) if source_hint else None
    report["model_dir"] = str(model_dir)

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("Saved evaluation report to {}", report_path)

    avg = report.get("average_judge_score")
    logger.info(
        "Evaluation complete. Average judge score: %s",
        f"{avg:.3f}" if isinstance(avg, (int, float)) else "N/A",
    )

    if args.verbose and "results" in report:
        for item in report["results"]:
            logger.info(
                "Sample %s | score=%s | prediction=%s",
                item.get("index"),
                item.get("judge_score"),
                item.get("prediction"),
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
