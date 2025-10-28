# 快速上手指南

本指南帮助你在最短时间内完成 Qwen3 Fine-tuner 的安装、运行与常见工作流。

## 1. 项目概览

Qwen3 Fine-tuner 是一个面向 Qwen3 模型的专业微调平台，具备以下能力：

- 完整的 Web 管理界面（Vue3 + Element Plus）
- 多种训练策略（SFT、LoRA、QLoRA、DPO、GRPO）
- 支持 Unsloth、FlashAttention-2 等训练加速方案
- JSON / JSONL / CSV / 纯文本等多种数据格式
- 实时训练监控、日志与进度追踪

## 2. 环境准备

### 2.1 克隆或进入项目目录

```bash
cd all4you
```

### 2.2 Python 虚拟环境（推荐）

```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 2.3 安装依赖

```bash
pip install -r requirements.txt
```

> 如需训练阶段的额外加速，可执行 `pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"`。

### 2.4 （可选）配置环境变量

```bash
cp .env.example .env
# 编辑 .env 并设置 Hugging Face 或 ModelScope 凭据
```

## 3. 启动服务

### 3.1 一键脚本

首选：

- Linux / macOS：`./scripts/deploy.sh`
- Windows：双击 `scripts\deploy.bat`

脚本会自动创建虚拟环境、安装依赖并并行启动后端与前端。如果你想快速进入本地开发模式，可使用 `./scripts/dev.sh`（假设依赖已就绪）；若想分别控制启动流程，可使用 `./scripts/start.sh` / `scripts\start.bat`。

### 3.2 手动启动

```bash
# 启动后端（默认端口 8000）
python backend/app.py

# 启动前端（默认端口 5173）
cd frontend
npm install   # 首次运行需要
npm run dev
```

启动完成后可访问：

- Web 界面：http://localhost:5173
- OpenAPI 文档：http://localhost:8000/docs
- ReDoc 文档：http://localhost:8000/redoc

## 4. 常用工作流

### 4.1 准备与上传数据

1. 在 **Data** 页面上传 JSON/JSONL/CSV/TXT 文件
2. 选择数据格式（Alpaca、ShareGPT 或 Raw）
3. 预览并确认字段映射

> 🆕 想用命令行一站式完成数据处理、训练与评测？运行 `python scripts/pipeline.py --data your.json --eval-ratio 0.1`，即可生成训练集、触发微调并输出自动评测报告。
>
> ⚡️ 想要“零配置”体验搜索意图场景？执行 `python scripts/pipeline.py --preset search-intent-lora` 会自动从魔搭拉取搜索意图数据集，并在 Qwen/Qwen3-0.6B 上进行 MPS LoRA 训练与评测。
>
> 🖥️ 使用 `--device auto/cuda/mps/cpu` 控制训练设备，`--judge-device` 可单独指定评测模型所在设备。macOS 用户可以直接运行 `python scripts/pipeline.py --data your.json --config backend/configs/qwen3-0.6b-mps.yaml --device mps --judge-model Qwen/Qwen3-0.6B`，脚本会自动调整精度与量化设置以适配 MPS。
>
> 📥 若数据托管在魔搭（ModelScope），可直接使用 `--moda-dataset content_understanding` 或 `--moda-dataset <dataset_id>` 自动下载、格式化并进入训练流程；如需仅下载，可执行 `./scripts/download_dataset.py --list` 查看预设并按需拉取。

示例数据格式：

```json
[
  {"instruction": "翻译成中文", "input": "Hello", "output": "你好"}
]
```

### 4.2 选择模型与配置

1. 在 **Models** 页面浏览可用模型
2. 在 **Training Configurations** 查看或复制模板
3. 若需自定义，编辑 `configs/` 目录下的 YAML 文件

### 4.3 启动训练与监控

1. 前往 **Training** 页面
2. 点击 **Start New Training**，填写任务名称、数据集、配置
3. 提交后实时查看训练进度、日志与指标

## 5. 目录速览

```
backend/ api/            # 数据、训练、模型、配置相关 API
backend/ core/           # 数据处理、数据库、训练引擎
backend/ models/         # Pydantic 数据模型
frontend/ src/           # 页面、组件、路由配置
configs/                 # 训练配置模板
examples/                # 示例数据
```

## 6. API 速查

- `POST /api/data/upload` — 上传训练数据
- `GET /api/data/list` — 查看数据文件
- `POST /api/train/start` — 启动训练任务
- `GET /api/train/status/{task_id}` — 获取任务状态
- `GET /api/models/list` — 查询可用模型
- `POST /api/config/validate` — 验证配置文件

完整 API 文档详见 http://localhost:8000/docs。

## 7. 故障排除

| 问题 | 排查步骤 |
| --- | --- |
| 后端无法启动 | 检查端口占用（`lsof -i :8000`），或通过 `HOST=0.0.0.0 PORT=8001 python backend/app.py` 变更端口 |
| 前端无法连接后端 | 确认 `frontend/vite.config.js` 代理配置指向正确的后端地址 |
| CUDA 内存不足 | 减小 `per_device_train_batch_size`、提高 `gradient_accumulation_steps`、启用 QLoRA 或 gradient checkpointing |
| 无法下载模型 | 确认网络、Hugging Face/ModelScope token 与 `USE_MODELSCOPE` 设置 |

## 8. 常见问答

- **如何添加自定义模型？** 编辑 `backend/api/models.py` 中的 `AVAILABLE_MODELS`。
- **如何配置 Hugging Face Token？** 在 `.env` 中设置 `HF_TOKEN=<your_token>` 并重启后端。
- **如何查看训练日志？** 后端日志位于 `backend/logs/`，并可在 Web 页面查看实时输出。
- **是否支持分布式训练？** 当前版本暂不支持，后续版本计划引入。

## 9. 性能参考

| 模型 | 标准训练 | Unsloth 加速 |
| --- | --- | --- |
| Qwen3-7B | 1x | 2-2.5x |
| Qwen3-14B | 1x | 2-2.5x |
| Qwen3-30B-A3B | 1x | 2-3x |

> 需要更多高级配置与诊断建议？请参考 [开发与测试手册](development.md)。
