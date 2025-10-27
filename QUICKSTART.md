# Qwen3 Fine-tuner Quick Start Guide

## 项目概览

Qwen3 Fine-tuner 是一个专业的 Qwen3 模型微调平台，提供：

- ✨ 完整的 Web 用户界面（Vue3 + Element Plus）
- 🚀 高效训练支持（Unsloth、FlashAttention-2、QLoRA）
- 📊 实时训练监控和日志
- 💾 灵活的数据格式支持（JSON、JSONL、CSV、TXT）
- ⚙️ 多种训练方法（SFT、LoRA、QLoRA、DPO、GRPO）
- 🤖 支持多个 Qwen3 模型

## 安装

### 1. 克隆或进入项目目录

```bash
cd qwen3-finetuner
```

### 2. 创建虚拟环境（推荐）

```bash
# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量（可选）

```bash
cp .env.example .env
# 编辑 .env 文件并设置你的 Hugging Face token
```

## 快速启动

### 一键启动（Linux/Mac）

```bash
chmod +x start.sh
./start.sh
```

### 一键启动（Windows）

```bash
start.bat
```

### 手动启动

#### 启动后端服务

```bash
cd backend
python app.py
```

后端将在 `http://localhost:8000` 运行

#### 启动前端应用（可选）

在新的终端窗口中：

```bash
cd frontend
npm install  # 仅第一次需要
npm run dev
```

前端将在 `http://localhost:5173` 运行

## 使用步骤

### 1. 访问应用

- **Web 界面**: http://localhost:5173
- **API 文档**: http://localhost:8000/docs
- **ReDoc 文档**: http://localhost:8000/redoc

### 2. 准备数据

数据需要采用以下格式之一：

#### Alpaca 格式（推荐）

JSON 文件：
```json
[
  {
    "instruction": "翻译成英文",
    "input": "你好",
    "output": "Hello"
  }
]
```

或 CSV 文件：
```csv
instruction,input,output
翻译成英文,你好,Hello
```

#### ShareGPT 格式

```json
[
  {
    "conversations": [
      {"from": "user", "value": "你好"},
      {"from": "assistant", "value": "你好！很高兴见到你"}
    ]
  }
]
```

#### 原始文本格式

```json
[
  {"text": "这是一条训练样本"},
  {"text": "这是另一条样本"}
]
```

### 3. 上传数据

1. 打开 Web 界面
2. 进入 **Data** 页面
3. 拖拽或点击上传数据文件
4. 选择数据格式（Alpaca、ShareGPT、Raw）

### 4. 选择模型和配置

1. 进入 **Models** 页面查看可用模型
2. 查看 **Training Configurations** 查看预设配置
3. 或在 **Training** 页面创建新配置

### 5. 启动训练

1. 进入 **Training** 页面
2. 点击 **Start New Training**
3. 选择：
   - 任务名称
   - 数据文件
   - 训练配置
4. 点击 **Start Training**
5. 监控训练进度

## 项目结构

```
qwen3-finetuner/
├── backend/                      # FastAPI 后端
│   ├── api/                     # API 路由
│   │   ├── data.py             # 数据管理 API
│   │   ├── training.py         # 训练管理 API
│   │   ├── models.py           # 模型管理 API
│   │   └── config.py           # 配置管理 API
│   ├── core/
│   │   ├── config.py           # 配置管理
│   │   ├── database.py         # 数据库定义
│   │   ├── data_processor.py   # 数据处理
│   │   └── trainer.py          # 训练引擎
│   ├── models/
│   │   └── schemas.py          # Pydantic 数据模型
│   ├── configs/
│   │   └── default.yaml        # 默认配置
│   └── app.py                  # FastAPI 主应用
│
├── frontend/                     # Vue3 前端
│   ├── src/
│   │   ├── pages/              # 页面组件
│   │   ├── router/             # 路由配置
│   │   ├── App.vue             # 主应用
│   │   └── main.js             # 入口
│   ├── vite.config.js          # Vite 配置
│   └── package.json
│
├── examples/
│   └── sample_data.json        # 示例数据
│
├── requirements.txt            # Python 依赖
├── README.md                   # 项目说明
└── QUICKSTART.md              # 本文件
```

## API 端点

### 数据管理

- `POST /api/data/upload` - 上传数据文件
- `GET /api/data/list` - 列出数据文件
- `GET /api/data/{file_id}` - 获取数据文件信息
- `POST /api/data/validate` - 验证数据格式
- `POST /api/data/preview` - 预览数据
- `DELETE /api/data/{file_id}` - 删除数据文件

### 训练管理

- `POST /api/train/start` - 启动训练任务
- `GET /api/train/status/{task_id}` - 获取训练状态
- `GET /api/train/list` - 列出所有任务
- `PATCH /api/train/{task_id}` - 更新任务
- `DELETE /api/train/{task_id}` - 删除任务

### 模型管理

- `GET /api/models/list` - 列出可用模型
- `GET /api/models/{model_name}` - 获取模型信息

### 配置管理

- `GET /api/config/list` - 列出配置
- `GET /api/config/{config_id}` - 获取配置
- `POST /api/config/create` - 创建新配置
- `DELETE /api/config/{config_id}` - 删除配置

## 配置说明

### 训练方法

- **SFT** (Supervised Fine-Tuning): 基础有监督微调，支持指令-输出对
- **LoRA**: 参数高效微调，适合资源有限的场景
- **QLoRA**: 量化 LoRA，结合 4 位量化，内存占用最少
- **DPO** (Direct Preference Optimization): 直接偏好优化，用于对齐
- **GRPO** (Group Relative Policy Optimization): 高效的偏好优化方法

### 量化选项

- **4-bit 量化**: 显著降低内存占用，推荐用于 QLoRA
- **8-bit 量化**: 平衡内存和性能
- **无量化**: 完整精度训练，需要更多 VRAM

### 优化技术

- **FlashAttention-2**: 加速注意力计算
- **Gradient Checkpointing**: 减少显存占用
- **Mixed Precision (bfloat16)**: 加速训练同时保持数值稳定

## 常见问题

### Q: 如何使用我自己的模型？

A: 修改 `backend/api/models.py` 中的 `AVAILABLE_MODELS` 字典，添加你的模型。

### Q: 如何设置 Hugging Face Token？

A:
1. 从 https://huggingface.co/settings/tokens 获取 token
2. 在 `.env` 文件中设置 `HF_TOKEN=your_token`
3. 重启后端服务

### Q: 训练速度太慢，如何加快？

A:
1. 启用 Unsloth（默认已启用）
2. 启用 FlashAttention-2
3. 增加 batch size（如果 VRAM 允许）
4. 使用 QLoRA 而不是完整 LoRA

### Q: 如何查看训练日志？

A: 日志保存在 `backend/logs/` 目录。实时训练信息在 Web 界面的任务详情中查看。

### Q: 支持分布式训练吗？

A: 当前不支持，计划在未来版本添加。

## 故障排除

### 后端无法启动

```bash
# 检查端口是否已被占用
lsof -i :8000

# 或者改变端口
HOST=0.0.0.0 PORT=8001 python backend/app.py
```

### 前端无法连接到后端

检查 `frontend/vite.config.js` 中的代理设置是否正确。

### CUDA 内存不足

1. 减小 `per_device_train_batch_size`
2. 增加 `gradient_accumulation_steps`
3. 使用 QLoRA 而不是 LoRA
4. 启用 gradient checkpointing

### 找不到模型

确保：
1. 设置了正确的 Hugging Face token
2. 互联网连接正常
3. 模型在 Hugging Face Hub 上存在

## 性能参考

使用 Unsloth + QLoRA 的速度对比：

| 模型 | 标准 | Unsloth |
|------|------|---------|
| Qwen3-7B | 1x | 2-2.5x |
| Qwen3-14B | 1x | 2-2.5x |
| Qwen3-30B-A3B | 1x | 2-3x |

内存占用对比：

| 配置 | 标准 | QLoRA |
|------|------|-------|
| LoRA | ~20GB | ~8GB |
| QLoRA | ~16GB | ~4GB |

## 许可证

MIT License

## 参考资源

- [Qwen3 官方文档](https://github.com/QwenLM/Qwen3)
- [Unsloth](https://github.com/unslothai/unsloth)
- [PEFT](https://github.com/huggingface/peft)
- [Transformers](https://huggingface.co/docs/transformers)

## 支持

如有问题，请提交 Issue 或 Pull Request。
