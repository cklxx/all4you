#!/usr/bin/env python3
"""
兼容性测试脚本 - 验证升级后的所有功能
"""

import sys
from pathlib import Path

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def test_imports():
    """测试所有关键模块导入"""
    print("=" * 60)
    print("1. 测试模块导入")
    print("=" * 60)

    modules_to_test = [
        ("FastAPI app", "app"),
        ("Core config", "core.config"),
        ("Core database", "core.database"),
        ("Core trainer", "core.trainer"),
        ("Core model_manager", "core.model_manager"),
        ("Core data_processor", "core.data_processor"),
        ("Core evaluator", "core.evaluator"),
        ("Models schemas", "models.schemas"),
        ("API routes", "api"),
    ]

    failed = []
    for name, module_path in modules_to_test:
        try:
            __import__(module_path)
            print(f"✅ {name}: OK")
        except Exception as e:
            print(f"❌ {name}: FAILED - {str(e)}")
            failed.append((name, str(e)))

    print()
    return len(failed) == 0, failed


def test_transformers_api():
    """测试 Transformers API 兼容性"""
    print("=" * 60)
    print("2. 测试 Transformers API 兼容性")
    print("=" * 60)

    try:
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            TrainingArguments,
            Trainer,
            BitsAndBytesConfig,
        )

        # 测试 BitsAndBytesConfig
        import torch
        config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        print("✅ BitsAndBytesConfig: OK")

        # 测试 TrainingArguments
        args = TrainingArguments(
            output_dir="./test_output",
            num_train_epochs=1,
            per_device_train_batch_size=1,
            save_steps=100,
        )
        print("✅ TrainingArguments: OK")

        print("✅ 所有 Transformers API 测试通过")
        print()
        return True, []
    except Exception as e:
        print(f"❌ Transformers API 测试失败: {str(e)}")
        print()
        return False, [("Transformers API", str(e))]


def test_peft_api():
    """测试 PEFT API 兼容性"""
    print("=" * 60)
    print("3. 测试 PEFT API 兼容性")
    print("=" * 60)

    try:
        from peft import LoraConfig, get_peft_model

        # 测试 LoraConfig
        lora_config = LoraConfig(
            r=64,
            lora_alpha=128,
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=["q_proj", "v_proj"],
        )
        print("✅ LoraConfig: OK")
        print("✅ PEFT API 测试通过")
        print()
        return True, []
    except Exception as e:
        print(f"❌ PEFT API 测试失败: {str(e)}")
        print()
        return False, [("PEFT API", str(e))]


def test_pydantic_schemas():
    """测试 Pydantic Schemas"""
    print("=" * 60)
    print("4. 测试 Pydantic Schemas")
    print("=" * 60)

    try:
        from models.schemas import (
            TrainingConfigCreate,
            TrainingConfigResponse,
            TrainingTaskResponse,
            ModelInfo,
            DownloadModelRequest,
        )

        # 测试 ModelInfo (有 model_name 和 model_size 字段)
        model_info = ModelInfo(
            model_name="Qwen/Qwen3-4B",
            model_size="4B",
            parameters=4000000000,
            max_seq_length=32768,
            description="Test model",
            supported_training_methods=["lora", "qlora"],
            recommended=True,
        )
        print(f"✅ ModelInfo: OK (model_name={model_info.model_name})")

        # 测试 TrainingConfigCreate
        config = TrainingConfigCreate(
            name="Test Config",
            model_name="Qwen/Qwen3-4B",
            training_method="lora",
        )
        print(f"✅ TrainingConfigCreate: OK")

        # 测试 DownloadModelRequest
        download_req = DownloadModelRequest(
            model_name="Qwen/Qwen3-4B",
            force_download=False,
        )
        print(f"✅ DownloadModelRequest: OK")

        print("✅ 所有 Pydantic schemas 测试通过")
        print()
        return True, []
    except Exception as e:
        print(f"❌ Pydantic schemas 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        print()
        return False, [("Pydantic schemas", str(e))]


def test_trainer_config():
    """测试 Trainer 配置"""
    print("=" * 60)
    print("5. 测试 Trainer 配置")
    print("=" * 60)

    try:
        from core.trainer import TrainingConfig, Trainer_Qwen3

        # 创建训练配置
        config = TrainingConfig(
            model_name="Qwen/Qwen3-4B",
            training_method="lora",
            device="cpu",  # 使用 CPU 避免 GPU 依赖
            num_train_epochs=1,
            load_in_4bit=False,  # CPU 不支持量化
        )
        print("✅ TrainingConfig: OK")

        # 初始化 Trainer（不加载模型）
        trainer = Trainer_Qwen3(config)
        print(f"✅ Trainer_Qwen3: OK (device={trainer.device})")

        print("✅ Trainer 配置测试通过")
        print()
        return True, []
    except Exception as e:
        print(f"❌ Trainer 配置测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        print()
        return False, [("Trainer config", str(e))]


def test_model_manager():
    """测试 Model Manager"""
    print("=" * 60)
    print("6. 测试 Model Manager")
    print("=" * 60)

    try:
        from core.model_manager import get_model_manager

        manager = get_model_manager()
        print(f"✅ ModelManager 初始化: OK")
        print(f"   缓存目录: {manager.cache_dir}")
        print(f"   使用 ModelScope: {manager.use_modelscope}")

        # 测试列出缓存模型
        cached = manager.list_cached_models()
        print(f"✅ 列出缓存模型: OK ({len(cached)} 个模型)")

        print("✅ Model Manager 测试通过")
        print()
        return True, []
    except Exception as e:
        print(f"❌ Model Manager 测试失败: {str(e)}")
        print()
        return False, [("Model Manager", str(e))]


def test_device_detection():
    """测试设备检测"""
    print("=" * 60)
    print("7. 测试设备检测")
    print("=" * 60)

    try:
        from core.devices import resolve_device, coerce_torch_dtype
        import torch

        device = resolve_device("auto")
        print(f"✅ 自动设备检测: {device}")

        dtype = coerce_torch_dtype(device)
        dtype_str = str(dtype).replace("torch.", "") if dtype else "None"
        print(f"✅ dtype 推断: {dtype_str}")

        print(f"✅ PyTorch 版本: {torch.__version__}")
        print(f"✅ CUDA 可用: {torch.cuda.is_available()}")
        print(f"✅ MPS 可用: {torch.backends.mps.is_available() if hasattr(torch.backends, 'mps') else False}")

        print("✅ 设备检测测试通过")
        print()
        return True, []
    except Exception as e:
        print(f"❌ 设备检测测试失败: {str(e)}")
        print()
        return False, [("Device detection", str(e))]


def print_version_info():
    """打印版本信息"""
    print("=" * 60)
    print("依赖版本信息")
    print("=" * 60)

    try:
        import torch
        print(f"PyTorch: {torch.__version__}")
    except:
        print("PyTorch: 未安装")

    try:
        import transformers
        print(f"Transformers: {transformers.__version__}")
    except:
        print("Transformers: 未安装")

    try:
        import peft
        print(f"PEFT: {peft.__version__}")
    except:
        print("PEFT: 未安装")

    try:
        import accelerate
        print(f"Accelerate: {accelerate.__version__}")
    except:
        print("Accelerate: 未安装")

    try:
        import bitsandbytes
        print(f"BitsAndBytes: {bitsandbytes.__version__}")
    except:
        print("BitsAndBytes: 未安装")

    try:
        import pydantic
        print(f"Pydantic: {pydantic.__version__}")
    except:
        print("Pydantic: 未安装")

    try:
        import fastapi
        print(f"FastAPI: {fastapi.__version__}")
    except:
        print("FastAPI: 未安装")

    print()


def main():
    """运行所有测试"""
    print("\n🚀 开始兼容性测试...\n")

    print_version_info()

    results = []
    all_errors = []

    # 运行所有测试
    tests = [
        test_imports,
        test_transformers_api,
        test_peft_api,
        test_pydantic_schemas,
        test_trainer_config,
        test_model_manager,
        test_device_detection,
    ]

    for test_func in tests:
        success, errors = test_func()
        results.append(success)
        all_errors.extend(errors)

    # 打印总结
    print("=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"通过: {passed}/{total}")
    print(f"失败: {total - passed}/{total}")

    if all_errors:
        print("\n失败的测试:")
        for name, error in all_errors:
            print(f"  ❌ {name}: {error}")

    print()

    if all(results):
        print("🎉 所有测试通过！升级后的代码完全兼容。")
        return 0
    else:
        print("⚠️  部分测试失败，请检查上述错误。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
