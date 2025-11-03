# Qwen3 Fine-tuner

一个专业的 Qwen3 模型微调平台，提供端到端的数据处理、训练编排以及现代化的 Web 界面。

> 📍 **项目路径**: `/Users/bytedance/code/learn/all4you`
> 🌏 **国内优化**: 深度集成 ModelScope，模型下载加速 5-10 倍
> 🚀 **推荐模型**: Qwen3-0.6B（快速验证） / Qwen3-4B（生产环境）
> 🐍 **Python 版本**: 3.10+ (推荐 3.12)
> 🔥 **最新更新**: 2025-10-28 - 升级依赖以支持 Python 3.12

## 文档索引

| 主题 | 内容概览 |
| --- | --- |
| [快速上手](docs/getting-started.md) | 安装、启动、常见工作流、故障排除与 FAQ |
| [常见问题 (FAQ)](docs/FAQ.md) | HF_TOKEN 说明、ModelScope 使用、常见错误解决 |
| [ModelScope 集成指南](docs/integrations/modelscope.md) | 国内镜像加速、缓存管理、CLI/Python 用法 |
| [开发与测试手册](docs/development.md) | 本地开发环境、代码风格、后端/前端测试命令 |
| [项目报告归档](docs/reports/README.md) | Bug 修复、阶段总结与交付报告索引 |

## 功能亮点

- ✨ **多种微调方法**：SFT、LoRA、QLoRA、DPO、GRPO
- 🚀 **高效训练**：Unsloth 加速、FlashAttention-2、混合精度
- 💾 **灵活数据处理**：支持 JSON、CSV、JSONL 等多种格式
- 🌐 **Web 控制台**：实时训练监控、模型管理、数据预览
- 🎯 **开箱即用**：内置训练配置模板与推荐模型
- 📊 **统一日志**：完整的训练日志、指标与任务进度

## 快速开始

### 方式一：使用 init.sh（推荐）

```bash
# 一键初始化环境（自动安装 uv 并配置虚拟环境）
./init.sh

# 激活虚拟环境
source .venv/bin/activate

# 启动应用
./scripts/start.sh
```

> **uv 优势**: 依赖安装速度比 pip 快 10-100 倍，自动管理虚拟环境

### 方式二：传统方式

1. **安装依赖**：`pip install -r requirements.txt`
2. **一键启动**：`./scripts/deploy.sh`（或在 Windows 上运行 `scripts\\deploy.bat`）
3. **手动启动后端**：`python backend/app.py`
4. **手动启动前端（可选）**：`cd frontend && npm install && npm run dev`
5. **访问服务**：
   - API 文档：http://localhost:8000/docs
   - Web 界面：http://localhost:5173

> 详细安装步骤与常见问题，请参见 [快速上手指南](docs/getting-started.md)。

### 一键数据处理 + 微调 + 评测

使用新的 CLI 脚本可在单条命令中完成数据清洗、模型训练与自动化评测：

```bash
python scripts/pipeline.py --data path/to/dataset.json --data-format alpaca --eval-ratio 0.1
```

脚本会将处理后的数据和评测结果保存在 `backend/outputs/pipeline-run/`（或 `--output-dir` 指定的目录）下，默认使用 `Qwen/Qwen3-4B` 作为评测模型，可通过 `--judge-model` 自定义或加上 `--no-judge` 关闭。如需更快验证，可指定 `--model` 或 `--judge-model Qwen/Qwen3-0.6B`。新增的 `--device` 参数可在 `auto/cuda/mps/cpu` 间切换训练设备，`--judge-device` 则允许单独控制评测模型的运行位置，`--fallback-judge-model` 则可配置主评测模型不可用时的自动回退策略。

> ⚡️ **一键搜索意图 LoRA**：运行 `python scripts/pipeline.py --preset search-intent-lora` 即可自动下载魔搭上的搜索意图数据集，使用 Qwen/Qwen3-0.6B 在 MPS 上进行 LoRA 微调，并优先调用本地 Ollama `qwen3:8b` 评测模型；若未安装 Ollama，则自动回退至 0.6B 完成打分。整个流程的产物会保存在 `backend/outputs/search-intent-lora/` 下。

> 💡 **Apple Silicon (MPS) 小贴士**：若需自定义数据或参数，也可参考预设中的设置执行 `python scripts/pipeline.py --data your.json --config backend/configs/qwen3-0.6b-mps.yaml --device mps --judge-model Qwen/Qwen3-0.6B`，脚本会自动关闭 4bit 量化、启用 fp16 并加载 0.6B 模型完成快速 LoRA 验证。

若希望直接从魔搭（ModelScope）拉取公开数据集，可使用新增的参数：

```bash
# 直接下载魔搭预设数据集并完成后续流程
python scripts/pipeline.py --moda-dataset content_understanding --moda-limit 2000

# 自定义字段映射与切分
python scripts/pipeline.py \
  --moda-dataset iic/nlp_search_intent \
  --moda-fields instruction=query,output=intent \
  --data-format alpaca
```

独立的数据下载工具位于 `scripts/download_dataset.py`，支持列出预设、只拉取原始数据或生成自定义映射：

```bash
./scripts/download_dataset.py --list
./scripts/download_dataset.py content_understanding --limit 500 --show-json
```

## 目录结构

```
all4you/
├── backend/                # 后端服务（FastAPI + SQLAlchemy）
│   ├── api/               # 数据、训练、模型等 API 路由
│   ├── core/              # 数据处理、训练引擎、模型管理
│   ├── models/            # Pydantic 模型定义
│   └── app.py             # FastAPI 应用入口
├── frontend/              # Vue3 + Element Plus 前端
│   └── src/              # 页面、组件与路由
├── docs/                  # 项目文档（指南、集成、报告）
│   ├── integrations/     # 外部服务与生态集成
│   ├── reports/          # 阶段性报告与总结
│   └── *.md              # 指南、手册等
├── examples/              # 示例数据与配置
├── requirements.txt       # Python 依赖列表
├── scripts/               # 自动化脚本与 CLI 工具
│   ├── deploy.sh / deploy.bat   # 零依赖一键部署脚本
│   ├── dev.sh                    # 本地开发便捷启动脚本
│   ├── setup.sh / setup.bat      # 依赖安装与环境检查
│   ├── start.sh / start.bat      # 手动启动后端 + 前端脚本
│   ├── pipeline.py              # 数据处理 + 训练 + 评测一键 CLI
│   └── download_dataset.py      # 魔搭数据集下载与字段映射工具
```

## 依赖版本

| 依赖 | 版本 | 说明 |
|-----|------|------|
| **Python** | 3.10+ (推荐 3.12) | 核心运行环境 |
| **PyTorch** | 2.9.0 | 深度学习框架 |
| **Transformers** | 4.57.1 | Hugging Face 模型库 |
| **PEFT** | 0.17.1 | 参数高效微调 |
| **Accelerate** | 1.11.0 | 多设备训练加速 |
| **FastAPI** | 0.104.1 | Web API 框架 |
| **Pydantic** | 2.5.0 | 数据验证 |

> 📋 完整依赖列表请查看 [requirements.txt](requirements.txt)
> 📝 版本升级说明请查看 [UPGRADE_NOTES.md](UPGRADE_NOTES.md)

## 开发与测试

- **后端依赖检查**：`python test_imports.py`
- **兼容性测试**：`python test_compatibility.py`
- **前端构建检查**：`cd frontend && npm run build`
- 更多开发细节、代码规范与诊断方法请参阅 [开发与测试手册](docs/development.md)。

## 许可证

本项目采用 [MIT](LICENSE) 开源协议。
