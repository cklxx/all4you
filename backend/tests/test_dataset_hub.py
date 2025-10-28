"""Tests for the ModelScope dataset helpers."""

from __future__ import annotations

import enum

import importlib.util
import types
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if "loguru" not in sys.modules:
    loguru_stub = types.ModuleType("loguru")

    class _DummyLogger:
        def __getattr__(self, name):  # pragma: no cover - simple stub
            return lambda *args, **kwargs: None

    loguru_stub.logger = _DummyLogger()  # type: ignore[attr-defined]
    sys.modules["loguru"] = loguru_stub

spec = importlib.util.spec_from_file_location(
    "dataset_hub", PROJECT_ROOT / "backend" / "core" / "dataset_hub.py"
)
assert spec is not None and spec.loader is not None
dataset_hub = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = dataset_hub
spec.loader.exec_module(dataset_hub)  # type: ignore[assignment]


class DummyFormations(enum.Enum):
    """Minimal stand-in for ModelScope's DatasetFormations enum."""

    hf_compatible = 1
    native = 2


def _reset_dummy_map() -> None:
    DummyFormations._value2member_map_ = {  # type: ignore[attr-defined]
        1: DummyFormations.hf_compatible,
        2: DummyFormations.native,
    }


def test_patch_modelscope_dataset_formations_adds_missing_values():
    _reset_dummy_map()

    patched = dataset_hub._patch_modelscope_dataset_formations(4, dataset_formations=DummyFormations)

    assert patched == [4]
    assert DummyFormations._value2member_map_[4] is DummyFormations.native  # type: ignore[index]


def test_patch_is_idempotent_for_existing_values():
    _reset_dummy_map()

    dataset_hub._patch_modelscope_dataset_formations(4, dataset_formations=DummyFormations)
    patched_again = dataset_hub._patch_modelscope_dataset_formations(4, dataset_formations=DummyFormations)

    assert patched_again == []


def test_maybe_patch_extracts_value_from_exception():
    _reset_dummy_map()

    exc = ValueError("4 is not a valid DatasetFormations")
    patched = dataset_hub._maybe_patch_modelscope_dataset_formations(
        exc, dataset_formations=DummyFormations
    )

    assert patched == [4]
    assert DummyFormations._value2member_map_[4] is DummyFormations.native  # type: ignore[index]

