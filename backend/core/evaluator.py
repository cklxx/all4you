"""Automatic evaluation utilities for fine-tuned Qwen models."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
from loguru import logger
from transformers import AutoModelForCausalLM, AutoTokenizer

from core.model_manager import get_model_manager


JUDGE_PROMPT_TEMPLATE = (
    "You are an expert evaluator. Given the instruction, optional input, reference answer, "
    "and the model answer, provide a JSON object with keys 'score' (1-5) and 'explanation'.\n"
    "Instruction: {instruction}\n"
    "Input: {input}\n"
    "Reference Answer: {reference}\n"
    "Model Answer: {prediction}\n"
    "Evaluation:"
)


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


class AutoEvaluator:
    """Run automatic evaluations for fine-tuned models."""

    def __init__(
        self,
        model_path: str,
        judge_model_name: Optional[str] = None,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> None:
        self.model_path = model_path
        self.judge_model_name = judge_model_name
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p

        self.model = None
        self.tokenizer = None
        self.judge_model = None
        self.judge_tokenizer = None

        self.model_manager = get_model_manager()

    def _load_target_model(self) -> None:
        if self.model is not None and self.tokenizer is not None:
            return

        model_path = Path(self.model_path)
        if model_path.exists():
            logger.info("Loading fine-tuned model from {}", model_path)
            self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                device_map="auto",
                trust_remote_code=True,
            )
        else:
            logger.info("Loading target model via model manager: {}", self.model_path)
            self.model, self.tokenizer = self.model_manager.load_model_and_tokenizer(
                self.model_path,
                device_map="auto",
                trust_remote_code=True,
            )

        self.model.eval()

    def _load_judge_model(self) -> None:
        if self.judge_model_name is None or self.judge_model_name.lower() == "none":
            return
        if self.judge_model is not None and self.judge_tokenizer is not None:
            return

        logger.info("Loading judge model: {}", self.judge_model_name)
        self.judge_model, self.judge_tokenizer = self.model_manager.load_model_and_tokenizer(
            self.judge_model_name,
            device_map="auto",
            trust_remote_code=True,
        )
        self.judge_model.eval()

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
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
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
        if self.judge_model is None or self.judge_tokenizer is None:
            return

        prompt = JUDGE_PROMPT_TEMPLATE.format(
            instruction=evaluation.instruction,
            input=evaluation.input_text or "(none)",
            reference=evaluation.reference or "(none)",
            prediction=evaluation.prediction or "(empty)",
        )
        inputs = self.judge_tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(self.judge_model.device) for k, v in inputs.items()}
        with torch.inference_mode():
            output = self.judge_model.generate(
                **inputs,
                max_new_tokens=128,
                temperature=0.0,
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

            if use_judge and self.judge_model is not None:
                self._judge(result)
                if result.judge_score is not None:
                    scores.append(result.judge_score)

            results.append(result)

        average_score = sum(scores) / len(scores) if scores else None
        report = {
            "total_samples": len(results),
            "average_judge_score": average_score,
            "judge_model": self.judge_model_name if use_judge else None,
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


__all__ = ["AutoEvaluator", "SampleEvaluation"]
