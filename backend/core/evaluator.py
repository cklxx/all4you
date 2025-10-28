"""Automatic evaluation utilities for fine-tuned Qwen models."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import shutil
import socket
import sys
import urllib.error
import urllib.request
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
from loguru import logger
from transformers import AutoModelForCausalLM, AutoTokenizer

from .model_manager import get_model_manager
from .devices import (
    resolve_device,
    ensure_device_environment,
    coerce_torch_dtype,
    torch_device,
)


JUDGE_PROMPT_TEMPLATE = (
    "You are an expert evaluator. Given the instruction, optional input, reference answer, "
    "and the model answer, provide a JSON object with keys 'score' (1-5) and 'explanation'.\n"
    "Instruction: {instruction}\n"
    "Input: {input}\n"
    "Reference Answer: {reference}\n"
    "Model Answer: {prediction}\n"
    "Evaluation:"
)

def _quiet_bitsandbytes_import() -> None:
    """Import bitsandbytes once while silencing noisy CPU-only warnings."""

    if "bitsandbytes" in sys.modules:  # already imported elsewhere
        return
    if importlib.util.find_spec("bitsandbytes") is None:
        return

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="The installed version of bitsandbytes was compiled without GPU support",
            category=UserWarning,
        )
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                import bitsandbytes  # type: ignore  # noqa: F401
        except Exception as exc:  # pragma: no cover - optional dependency
            logger.debug("bitsandbytes import failed: {}", exc)


@dataclass
class SampleEvaluation:
    """Result of evaluating a single sample."""

    index: int
    instruction: str
    input_text: str
    reference: str
    prediction: str
    judge_score: Optional[float] = None
    judge_explanation: Optional[str] = None
    judge_raw: Optional[str] = None


class OllamaJudgeUnavailable(RuntimeError):
    """Raised when an Ollama judge model cannot be reached."""


class OllamaJudgeClient:
    """Minimal HTTP client for interacting with a local Ollama server."""

    def __init__(
        self,
        model_name: str,
        *,
        base_url: str = "http://127.0.0.1:11434",
        health_timeout: float = 2.0,
        request_timeout: float = 60.0,
    ) -> None:
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.health_timeout = health_timeout
        self.request_timeout = request_timeout

    def _is_server_available(self) -> bool:
        """Best-effort probe to check whether the Ollama server is reachable."""

        if shutil.which("ollama") is None:
            return False

        try:
            request = urllib.request.Request(
                f"{self.base_url}/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=self.health_timeout) as response:  # type: ignore[arg-type]
                return 200 <= response.status < 300
        except Exception:  # pragma: no cover - environment dependent
            return False

    def ensure_available(self) -> None:
        if not self._is_server_available():  # pragma: no cover - environment dependent
            raise OllamaJudgeUnavailable(
                "未检测到可用的 Ollama 服务，请确保已经安装并启动 Ollama。"
            )

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0},
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.request_timeout) as response:  # type: ignore[arg-type]
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:  # pragma: no cover - environment dependent
            error_detail = ""
            try:
                raw = exc.read()  # type: ignore[attr-defined]
            except Exception:
                raw = b""
            if raw:
                try:
                    parsed_error = json.loads(raw.decode("utf-8"))
                    candidate = parsed_error.get("error") or parsed_error.get("message")
                    if isinstance(candidate, str):
                        error_detail = candidate.strip()
                except Exception:
                    error_detail = raw.decode("utf-8", "ignore").strip()
            if exc.code == 404:
                message = f"未在 Ollama 中找到评测模型 '{self.model_name}'。"
                if error_detail:
                    message = f"{message} {error_detail}"
                advice = (
                    f" 请通过 `ollama pull {self.model_name}` 下载安装该模型，或使用 `--judge-model` "
                    "指定已安装的评测模型。"
            )
                raise OllamaJudgeUnavailable(message + advice)
            message = f"Ollama 评测接口返回错误（HTTP {exc.code}"
            if exc.reason:  # type: ignore[truthy-function]
                message += f": {exc.reason}"
            message += "）。"
            if error_detail:
                message = f"{message} {error_detail}"
            raise OllamaJudgeUnavailable(message)
        except (TimeoutError, socket.timeout) as exc:  # pragma: no cover - environment dependent
            raise OllamaJudgeUnavailable(
                "连接 Ollama 评测服务超时，请确认服务已启动并可访问。"
            ) from exc
        except urllib.error.URLError as exc:  # pragma: no cover - environment dependent
            raise OllamaJudgeUnavailable(str(exc))

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"无法解析 Ollama 返回的内容: {exc}")

        text = parsed.get("response")
        if not isinstance(text, str):
            raise RuntimeError("Ollama 响应缺少 'response' 字段或类型不正确。")
        return text.strip()


class AutoEvaluator:
    """Run automatic evaluations for fine-tuned models."""

    def __init__(
        self,
        model_path: str,
        judge_model_name: Optional[str] = None,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        device: str = "auto",
        judge_device: Optional[str] = None,
    ) -> None:
        self.model_path = model_path
        self.judge_model_name = judge_model_name
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.device = resolve_device(device)
        ensure_device_environment(self.device)
        judge_pref = judge_device if judge_device is not None else device
        self.judge_device = resolve_device(judge_pref)
        ensure_device_environment(self.judge_device)

        self.model = None
        self.tokenizer = None
        self.judge_model = None
        self.judge_tokenizer = None
        self._ollama_judge: Optional[OllamaJudgeClient] = None
        self.active_judge_model_name: Optional[str] = None
        self.target_dtype = coerce_torch_dtype(
            self.device,
            prefer_fp16=True,
        )
        self.judge_dtype = coerce_torch_dtype(
            self.judge_device,
            prefer_fp16=True,
        )
        self.torch_device = torch_device(self.device)
        self.judge_torch_device = torch_device(self.judge_device)

        self.model_manager = get_model_manager()

    def _load_target_model(self) -> None:
        if self.model is not None and self.tokenizer is not None:
            return

        model_path = Path(self.model_path)
        if model_path.exists():
            logger.info("Loading fine-tuned model from {}", model_path)
            _quiet_bitsandbytes_import()
            self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                device_map="auto" if self.device == "cuda" else None,
                torch_dtype=self.target_dtype,
                trust_remote_code=True,
            )
            self.model.to(self.torch_device)
        else:
            logger.info("Loading target model via model manager: {}", self.model_path)
            _quiet_bitsandbytes_import()
            self.model, self.tokenizer = self.model_manager.load_model_and_tokenizer(
                self.model_path,
                device_map="auto" if self.device == "cuda" else None,
                trust_remote_code=True,
                device=self.device,
                torch_dtype=self.target_dtype,
            )

        self.model.eval()

    def _load_judge_model(self) -> None:
        if self.judge_model_name is None or self.judge_model_name.lower() == "none":
            return
        if self.judge_model is not None and self.judge_tokenizer is not None:
            return

        normalized = self.judge_model_name.strip()
        if normalized.startswith("ollama:"):
            ollama_model = normalized.split(":", 1)[1].strip()
        elif normalized.startswith("ollama/"):
            ollama_model = normalized.split("/", 1)[1].strip()
        else:
            ollama_model = None

        if ollama_model:
            self._ollama_judge = OllamaJudgeClient(ollama_model)
            self._ollama_judge.ensure_available()
            self.active_judge_model_name = f"ollama:{ollama_model}"
            logger.info("Using Ollama judge model: {}", self.active_judge_model_name)
            return

        logger.info("Loading judge model: {}", self.judge_model_name)
        _quiet_bitsandbytes_import()
        self.judge_model, self.judge_tokenizer = self.model_manager.load_model_and_tokenizer(
            self.judge_model_name,
            device_map="auto" if self.judge_device == "cuda" else None,
            trust_remote_code=True,
            device=self.judge_device,
            torch_dtype=self.judge_dtype,
        )
        self.judge_model.eval()
        self.active_judge_model_name = self.judge_model_name

    @staticmethod
    def _extract_text(sample: Dict[str, Any], format_type: str) -> tuple[str, str, str]:
        if format_type == "alpaca":
            instruction = str(sample.get("instruction", "")).strip()
            input_text = str(sample.get("input", "")).strip()
            reference = str(sample.get("output", "")).strip()
        elif format_type == "sharegpt":
            conversation = sample.get("conversations", []) or []
            instruction_parts: List[str] = []
            reference = ""
            for turn in conversation:
                role = turn.get("from")
                value = str(turn.get("value", ""))
                if role == "user":
                    instruction_parts.append(value)
                elif role == "assistant":
                    reference = value
            instruction = "\n".join(instruction_parts)
            input_text = ""
        else:
            instruction = str(sample.get("text", "")).strip()
            input_text = ""
            reference = sample.get("output") or ""
        return instruction, input_text, reference

    @staticmethod
    def _build_prompt(instruction: str, input_text: str) -> str:
        prompt = instruction.strip()
        if input_text:
            prompt = f"{prompt}\n{input_text.strip()}"
        return prompt.strip()

    def _generate(self, prompt: str) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(self.torch_device) for k, v in inputs.items()}
        with torch.inference_mode():
            output = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                do_sample=self.temperature > 0,
                pad_token_id=self.tokenizer.pad_token_id,
            )
        generated_ids = output[0][inputs["input_ids"].shape[1]:]
        prediction = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        return prediction.strip()

    def _judge(self, evaluation: SampleEvaluation) -> None:
        prompt = JUDGE_PROMPT_TEMPLATE.format(
            instruction=evaluation.instruction,
            input=evaluation.input_text or "(none)",
            reference=evaluation.reference or "(none)",
            prediction=evaluation.prediction or "(empty)",
        )

        if self._ollama_judge is not None:
            raw_text = self._ollama_judge.generate(prompt)
            evaluation.judge_raw = raw_text
            match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
            candidate = match.group(0) if match else raw_text
            try:
                parsed = json.loads(candidate)
                score = float(parsed.get("score")) if "score" in parsed else None
                explanation = (
                    str(parsed.get("explanation", "")).strip() if parsed else ""
                )
            except Exception:  # pragma: no cover - heuristic fallback
                score_match = re.search(r"([1-5](?:\.\d+)?)", raw_text)
                score = float(score_match.group(1)) if score_match else None
                explanation = raw_text

            evaluation.judge_score = score
            evaluation.judge_explanation = explanation
            return

        if self.judge_model is None or self.judge_tokenizer is None:
            return

        inputs = self.judge_tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(self.judge_torch_device) for k, v in inputs.items()}
        with torch.inference_mode():
            output = self.judge_model.generate(
                **inputs,
                max_new_tokens=128,
                temperature=1.0,
                do_sample=False,
                pad_token_id=self.judge_tokenizer.pad_token_id,
            )
        generated_ids = output[0][inputs["input_ids"].shape[1]:]
        raw_text = self.judge_tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        evaluation.judge_raw = raw_text

        match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
        candidate = match.group(0) if match else raw_text
        try:
            parsed = json.loads(candidate)
            score = float(parsed.get("score")) if "score" in parsed else None
            explanation = str(parsed.get("explanation", "")).strip() if parsed else ""
        except Exception:  # pragma: no cover - heuristic fallback
            score_match = re.search(r"([1-5](?:\.\d+)?)", raw_text)
            score = float(score_match.group(1)) if score_match else None
            explanation = raw_text

        evaluation.judge_score = score
        evaluation.judge_explanation = explanation

    def evaluate(
        self,
        samples: List[Dict[str, Any]],
        format_type: str = "alpaca",
        use_judge: bool = True,
    ) -> Dict[str, Any]:
        if not samples:
            raise ValueError("No samples provided for evaluation")

        self._load_target_model()
        if use_judge:
            self.active_judge_model_name = None
            self._load_judge_model()

        results: List[SampleEvaluation] = []
        scores: List[float] = []

        for idx, sample in enumerate(samples):
            instruction, input_text, reference = self._extract_text(sample, format_type)
            prompt = self._build_prompt(instruction, input_text)
            if not prompt:
                logger.warning("Skipping sample {} due to empty prompt", idx)
                continue

            prediction = self._generate(prompt)
            result = SampleEvaluation(
                index=idx,
                instruction=instruction,
                input_text=input_text,
                reference=reference,
                prediction=prediction,
            )

            if use_judge and (self.judge_model is not None or self._ollama_judge is not None):
                self._judge(result)
                if result.judge_score is not None:
                    scores.append(result.judge_score)

            results.append(result)

        average_score = sum(scores) / len(scores) if scores else None
        report = {
            "total_samples": len(results),
            "average_judge_score": average_score,
            "judge_model": self.active_judge_model_name if use_judge else None,
            "requested_judge_model": self.judge_model_name if use_judge else None,
            "results": [
                {
                    "index": r.index,
                    "instruction": r.instruction,
                    "input": r.input_text,
                    "reference": r.reference,
                    "prediction": r.prediction,
                    "judge_score": r.judge_score,
                    "judge_explanation": r.judge_explanation,
                    "judge_raw": r.judge_raw,
                }
                for r in results
            ],
        }
        return report


__all__ = ["AutoEvaluator", "OllamaJudgeUnavailable", "SampleEvaluation"]
