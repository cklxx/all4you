"""Utilities for downloading datasets from ModelScope (魔搭)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from loguru import logger

try:  # pragma: no cover - optional dependency
    from modelscope.msdatasets import MsDataset
    HAS_MODELSCOPE = True
except ImportError:  # pragma: no cover - handled at runtime
    MsDataset = None  # type: ignore
    HAS_MODELSCOPE = False


@dataclass(frozen=True)
class ModelScopeDatasetConfig:
    """Configuration for a ModelScope dataset pull."""

    name: str
    dataset_id: str
    split: str = "train"
    subset: Optional[str] = None
    fields: Dict[str, str] = field(default_factory=dict)
    description: Optional[str] = None

    def with_overrides(
        self,
        split: Optional[str] = None,
        subset: Optional[str] = None,
        fields: Optional[Dict[str, str]] = None,
    ) -> "ModelScopeDatasetConfig":
        return ModelScopeDatasetConfig(
            name=self.name,
            dataset_id=self.dataset_id,
            split=split or self.split,
            subset=subset if subset is not None else self.subset,
            fields={**self.fields, **(fields or {})},
            description=self.description,
        )


def _ensure_modelscope_available() -> None:
    if not HAS_MODELSCOPE or MsDataset is None:  # pragma: no cover - runtime guard
        raise RuntimeError(
            "modelscope package is required but not installed. "
            "Install it with `pip install modelscope`."
        )


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if hasattr(value, "tolist"):
        try:
            value = value.tolist()
        except Exception:  # pragma: no cover - best effort conversion
            pass
    if isinstance(value, (list, tuple)):
        return "\n".join(_stringify(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _resolve_template(template: Optional[str], record: Dict[str, Any]) -> str:
    if not template:
        return ""
    if "{" in template and "}" in template:
        try:
            return template.format(**record)
        except Exception:  # pragma: no cover - best effort formatting
            logger.debug("Failed to format template '%s' with record keys %s", template, record.keys())
    return _stringify(record.get(template, template))


def _normalize_records(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for sample in records:
        normalized.append({k: sample[k] for k in sample})
    return normalized


class ModelScopeDatasetManager:
    """Download and adapt datasets hosted on ModelScope."""

    PRESET_DATASETS: Dict[str, ModelScopeDatasetConfig] = {
        "alpaca_zh": ModelScopeDatasetConfig(
            name="alpaca_zh",
            dataset_id="AI-ModelScope/alpaca-gpt4-data-zh",
            split="train",
            fields={
                "instruction": "instruction",
                "input": "input",
                "output": "output",
            },
            description="中文 Alpaca 数据集，GPT-4 生成的高质量指令数据",
        ),
        "firefly": ModelScopeDatasetConfig(
            name="firefly",
            dataset_id="wyj123456/firefly-train-1.1M",
            split="train",
            fields={
                "instruction": "{input}",
                "input": "",
                "output": "target",
            },
            description="Firefly 中文对话数据集，包含 110 万条数据",
        ),
        "belle": ModelScopeDatasetConfig(
            name="belle",
            dataset_id="AI-ModelScope/train_0.5M_CN",
            split="train",
            fields={
                "instruction": "instruction",
                "input": "input",
                "output": "output",
            },
            description="BELLE 中文指令数据集 50 万条",
        ),
    }

    def __init__(self, cache_dir: Optional[Path | str] = None) -> None:
        self.cache_dir = Path(cache_dir or "datasets/modelscope").resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def list_presets(cls) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "dataset_id": cfg.dataset_id,
                "split": cfg.split,
                "subset": cfg.subset,
                "fields": cfg.fields,
                "description": cfg.description,
            }
            for name, cfg in cls.PRESET_DATASETS.items()
        }

    def resolve_config(
        self,
        name_or_id: str,
        split: Optional[str] = None,
        subset: Optional[str] = None,
        fields: Optional[Dict[str, str]] = None,
    ) -> ModelScopeDatasetConfig:
        if name_or_id in self.PRESET_DATASETS:
            base = self.PRESET_DATASETS[name_or_id]
        else:
            base = ModelScopeDatasetConfig(
                name=name_or_id,
                dataset_id=name_or_id,
                split="train",
            )
        return base.with_overrides(split=split, subset=subset, fields=fields)

    def _download_raw(
        self, config: ModelScopeDatasetConfig, limit: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], Path]:
        _ensure_modelscope_available()

        logger.info(
            "Downloading ModelScope dataset '%s' (split=%s, subset=%s)",
            config.dataset_id,
            config.split,
            config.subset,
        )

        # Load dataset with minimal parameters for better compatibility
        try:
            # Try with split parameter
            dataset = MsDataset.load(
                config.dataset_id,
                split=config.split,
            )
        except Exception as e:
            logger.warning(f"Failed to load with split parameter: {e}")
            try:
                # Fallback: try without any optional parameters
                dataset = MsDataset.load(config.dataset_id)
            except Exception as e2:
                logger.error(f"Failed to load dataset: {e2}")
                raise RuntimeError(
                    f"Cannot load dataset {config.dataset_id}. "
                    f"Please verify the dataset exists on ModelScope. "
                    f"Error: {e2}"
                )
        records: List[Dict[str, Any]] = []
        for idx, sample in enumerate(dataset):
            if limit is not None and idx >= limit:
                break
            if hasattr(sample, "to_dict"):
                sample_dict = sample.to_dict()
            else:
                sample_dict = dict(sample)
            records.append(sample_dict)

        save_dir = self.cache_dir / config.name.replace("/", "_")
        save_dir.mkdir(parents=True, exist_ok=True)
        raw_path = save_dir / f"{config.split}.raw.json"
        raw_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        logger.info("Saved raw dataset snapshot to %s", raw_path)
        return records, raw_path

    @staticmethod
    def _apply_field_mapping(
        records: Iterable[Dict[str, Any]], fields: Dict[str, str]
    ) -> List[Dict[str, str]]:
        mapped: List[Dict[str, str]] = []
        for sample in records:
            record: Dict[str, str] = {}
            for target, source in fields.items():
                if source == "":
                    record[target] = ""
                else:
                    record[target] = _resolve_template(source, sample)
            mapped.append(record)
        return mapped

    def download(
        self,
        name_or_id: str,
        split: Optional[str] = None,
        subset: Optional[str] = None,
        fields: Optional[Dict[str, str]] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        config = self.resolve_config(name_or_id, split=split, subset=subset, fields=fields)
        raw_records, raw_path = self._download_raw(config, limit=limit)
        normalized_raw = _normalize_records(raw_records)

        formatted_records: Optional[List[Dict[str, str]]] = None
        formatted_path: Optional[Path] = None
        if config.fields:
            formatted_records = self._apply_field_mapping(normalized_raw, config.fields)
            formatted_path = raw_path.with_suffix(".formatted.json")
            formatted_path.write_text(
                json.dumps(formatted_records, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            logger.info("Saved formatted dataset snapshot to %s", formatted_path)

        return {
            "config": config,
            "raw_records": normalized_raw,
            "formatted_records": formatted_records,
            "raw_path": str(raw_path),
            "formatted_path": str(formatted_path) if formatted_path else None,
        }

    def prepare_for_training(
        self,
        name_or_id: str,
        split: Optional[str] = None,
        subset: Optional[str] = None,
        fields: Optional[Dict[str, str]] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        download_info = self.download(
            name_or_id=name_or_id,
            split=split,
            subset=subset,
            fields=fields,
            limit=limit,
        )
        data_path = download_info["formatted_path"] or download_info["raw_path"]
        return {
            **download_info,
            "data_path": data_path,
        }
