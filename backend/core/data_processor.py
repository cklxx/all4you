"""
Data processing and loading utilities for fine-tuning datasets
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from loguru import logger

try:  # Optional dependency, only required for dataset creation
    from datasets import Dataset
except ImportError:  # pragma: no cover - handled gracefully in runtime
    Dataset = None

class DataProcessor:
    """Process various data formats into training datasets"""

    # Supported formats
    SUPPORTED_FORMATS = ["json", "jsonl", "csv", "txt"]
    SUPPORTED_STRUCTURES = ["alpaca", "sharegpt", "raw"]

    @staticmethod
    def load_json(file_path: str) -> List[Dict[str, Any]]:
        """Load JSON file"""
        logger.info(f"Loading JSON file: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} samples from JSON file")
        return data

    @staticmethod
    def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
        """Load JSONL file"""
        logger.info(f"Loading JSONL file: {file_path}")
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
        logger.info(f"Loaded {len(data)} samples from JSONL file")
        return data

    @staticmethod
    def load_csv(file_path: str) -> List[Dict[str, Any]]:
        """Load CSV file"""
        logger.info(f"Loading CSV file: {file_path}")
        df = pd.read_csv(file_path)
        data = df.to_dict('records')
        logger.info(f"Loaded {len(data)} samples from CSV file")
        return data

    @staticmethod
    def load_txt(file_path: str, format_type: str = "raw") -> List[Dict[str, Any]]:
        """Load TXT file"""
        logger.info(f"Loading TXT file: {file_path}")
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            if format_type == "raw":
                # Each line is a sample
                for line in f:
                    if line.strip():
                        data.append({"text": line.strip()})
            elif format_type == "sharegpt":
                # Multi-line format with separators
                current_sample = {"text": ""}
                for line in f:
                    if line.strip() == "---":
                        if current_sample["text"]:
                            data.append(current_sample)
                        current_sample = {"text": ""}
                    else:
                        current_sample["text"] += line
                if current_sample["text"]:
                    data.append(current_sample)
        logger.info(f"Loaded {len(data)} samples from TXT file")
        return data

    @classmethod
    def load_file(cls, file_path: str, file_type: Optional[str] = None,
                  format_type: str = "alpaca") -> List[Dict[str, Any]]:
        """
        Load data file based on file type

        Args:
            file_path: Path to the data file
            file_type: File type (json, jsonl, csv, txt). If None, inferred from extension
            format_type: Data format structure (alpaca, sharegpt, raw)

        Returns:
            List of data samples
        """
        path = Path(file_path)

        # Infer file type if not provided
        if file_type is None:
            file_type = path.suffix.lstrip('.').lower()

        if file_type not in cls.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported file type: {file_type}. Supported: {cls.SUPPORTED_FORMATS}")

        # Load file based on type
        if file_type == "json":
            data = cls.load_json(file_path)
        elif file_type == "jsonl":
            data = cls.load_jsonl(file_path)
        elif file_type == "csv":
            data = cls.load_csv(file_path)
        elif file_type == "txt":
            data = cls.load_txt(file_path, format_type)

        return data

    @staticmethod
    def format_alpaca(data: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Convert to Alpaca format
        Expected keys: instruction, input, output
        """
        formatted = []
        for sample in data:
            if isinstance(sample, dict):
                formatted_sample = {}

                # Handle instruction
                if "instruction" in sample:
                    formatted_sample["instruction"] = str(sample["instruction"])
                elif "prompt" in sample:
                    formatted_sample["instruction"] = str(sample["prompt"])
                else:
                    formatted_sample["instruction"] = ""

                # Handle input
                if "input" in sample:
                    formatted_sample["input"] = str(sample["input"])
                else:
                    formatted_sample["input"] = ""

                # Handle output
                if "output" in sample:
                    formatted_sample["output"] = str(sample["output"])
                elif "response" in sample:
                    formatted_sample["output"] = str(sample["response"])
                elif "text" in sample:
                    formatted_sample["output"] = str(sample["text"])
                else:
                    formatted_sample["output"] = ""

                formatted.append(formatted_sample)

        return formatted

    @staticmethod
    def format_sharegpt(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert to ShareGPT format
        Expected format: conversations with role and content
        """
        formatted = []
        for sample in data:
            if isinstance(sample, dict):
                if "conversations" in sample:
                    formatted.append(sample)
                elif "text" in sample:
                    # Convert raw text to conversation format
                    formatted.append({
                        "conversations": [
                            {"from": "user", "value": sample["text"]}
                        ]
                    })
                else:
                    # Try to construct from available fields
                    user_content = sample.get("instruction") or sample.get("input", "")
                    assistant_content = sample.get("output", "")
                    formatted.append({
                        "conversations": [
                            {"from": "user", "value": user_content},
                            {"from": "assistant", "value": assistant_content}
                        ]
                    })

        return formatted

    @staticmethod
    def format_raw(data: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Keep raw text format
        """
        formatted = []
        for sample in data:
            if isinstance(sample, dict):
                if "text" in sample:
                    formatted.append({"text": sample["text"]})
                else:
                    # Concatenate all fields
                    text = " ".join(str(v) for v in sample.values())
                    formatted.append({"text": text})

        return formatted

    @classmethod
    def format_data(cls, data: List[Dict[str, Any]], format_type: str = "alpaca") -> List[Dict[str, Any]]:
        """
        Format data to specified format

        Args:
            data: Raw data list
            format_type: Target format (alpaca, sharegpt, raw)

        Returns:
            Formatted data list
        """
        if format_type == "alpaca":
            return cls.format_alpaca(data)
        elif format_type == "sharegpt":
            return cls.format_sharegpt(data)
        elif format_type == "raw":
            return cls.format_raw(data)
        else:
            raise ValueError(f"Unsupported format type: {format_type}")

    @classmethod
    def load_and_format_data(cls, file_path: str, format_type: str = "alpaca",
                            file_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Load and format data in one step

        Args:
            file_path: Path to data file
            format_type: Target format
            file_type: Source file type

        Returns:
            Formatted data list
        """
        logger.info(f"Loading and formatting data: {file_path} -> {format_type}")

        # Load data
        data = cls.load_file(file_path, file_type, format_type)

        # Format data
        formatted_data = cls.format_data(data, format_type)

        logger.info(f"Processed {len(formatted_data)} samples")
        return formatted_data

    @staticmethod
    def create_huggingface_dataset(data: List[Dict[str, Any]], format_type: str = "alpaca") -> Dataset:
        """
        Create Hugging Face Dataset from data

        Args:
            data: List of data samples
            format_type: Data format type

        Returns:
            Hugging Face Dataset
        """
        if Dataset is None:
            raise ImportError(
                "datasets library is required to create Hugging Face datasets. Install it with 'pip install datasets'."
            )

        logger.info(f"Creating Hugging Face dataset with {len(data)} samples")

        if format_type == "alpaca":
            # Create from Alpaca format
            dataset = Dataset.from_dict({
                "instruction": [s.get("instruction", "") for s in data],
                "input": [s.get("input", "") for s in data],
                "output": [s.get("output", "") for s in data],
            })
        elif format_type == "sharegpt":
            # Create from ShareGPT format
            dataset = Dataset.from_dict({
                "conversations": [s.get("conversations", []) for s in data],
            })
        else:
            # Create from raw format
            dataset = Dataset.from_dict({
                "text": [s.get("text", "") for s in data],
            })

        logger.info(f"Created dataset with {len(dataset)} samples")
        return dataset


def validate_data_format(data: List[Dict[str, Any]], format_type: str = "alpaca") -> Dict[str, Any]:
    """
    Validate data format and return statistics

    Args:
        data: Data to validate
        format_type: Expected format

    Returns:
        Validation report
    """
    report = {
        "valid": True,
        "total_samples": len(data),
        "issues": [],
        "statistics": {}
    }

    if not data:
        report["valid"] = False
        report["issues"].append("No samples found")
        return report

    if format_type == "alpaca":
        missing_instruction = sum(1 for s in data if not s.get("instruction"))
        missing_output = sum(1 for s in data if not s.get("output"))

        if missing_instruction > 0:
            report["issues"].append(f"{missing_instruction} samples missing 'instruction'")
        if missing_output > 0:
            report["issues"].append(f"{missing_output} samples missing 'output'")

        report["statistics"] = {
            "avg_instruction_length": sum(len(str(s.get("instruction", ""))) for s in data) / len(data),
            "avg_output_length": sum(len(str(s.get("output", ""))) for s in data) / len(data),
        }

    elif format_type == "sharegpt":
        invalid_conversations = sum(1 for s in data if not isinstance(s.get("conversations"), list))
        if invalid_conversations > 0:
            report["issues"].append(f"{invalid_conversations} samples have invalid conversations format")

        report["statistics"] = {
            "avg_conversations_per_sample": sum(len(s.get("conversations", [])) for s in data) / len(data),
        }

    if report["issues"]:
        report["valid"] = False

    return report
