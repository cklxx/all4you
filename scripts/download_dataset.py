#!/usr/bin/env python3
"""Utility CLI for downloading datasets from ModelScope (魔搭)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger

from backend.core.dataset_hub import ModelScopeDatasetManager


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download datasets from ModelScope with optional preset mappings."
    )
    parser.add_argument(
        "dataset",
        nargs="?",
        help="Preset name or dataset_id from ModelScope (魔搭).",
    )
    parser.add_argument(
        "--split",
        default=None,
        help="Dataset split to download (default defined by preset).",
    )
    parser.add_argument(
        "--subset",
        default=None,
        help="Optional subset name for the dataset.",
    )
    parser.add_argument(
        "--fields",
        default=None,
        help=(
            "Comma separated mapping for instruction/input/output fields, e.g. "
            "instruction=query,input=context,output=answer."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of samples downloaded.",
    )
    parser.add_argument(
        "--cache-dir",
        default="datasets/modelscope",
        help="Directory to store downloaded datasets.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available presets bundled with the project.",
    )
    parser.add_argument(
        "--show-json",
        action="store_true",
        help="Print the download metadata as JSON after completion.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    if args.list:
        presets = ModelScopeDatasetManager.list_presets()
        if not presets:
            logger.info("No presets bundled. Specify dataset_id manually.")
            return 0
        logger.info("Available ModelScope presets:")
        for name, info in presets.items():
            logger.info(
                "- %s: %s (split=%s, subset=%s)",
                name,
                info["dataset_id"],
                info["split"],
                info.get("subset"),
            )
            if info.get("description"):
                logger.info("    %s", info["description"])
        return 0

    if not args.dataset:
        logger.error("Please provide a dataset preset name or dataset_id.")
        return 1

    try:
        field_mapping = parse_field_mapping(args.fields)
    except ValueError as exc:
        logger.error(str(exc))
        return 1

    manager = ModelScopeDatasetManager(cache_dir=args.cache_dir)
    try:
        info = manager.prepare_for_training(
            name_or_id=args.dataset,
            split=args.split,
            subset=args.subset,
            fields=field_mapping or None,
            limit=args.limit,
        )
    except Exception as exc:  # pragma: no cover - external dependency call
        logger.error("Failed to download dataset: {}", exc)
        return 1

    logger.info("Dataset stored at: %s", info["data_path"])
    if args.show_json:
        payload = {
            "dataset": args.dataset,
            "config": {
                "dataset_id": info["config"].dataset_id,
                "split": info["config"].split,
                "subset": info["config"].subset,
                "fields": info["config"].fields,
            },
            "raw_path": info["raw_path"],
            "formatted_path": info.get("formatted_path"),
            "limit": args.limit,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
