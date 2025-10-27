# Qwen3 Fine-tuner

一个专业的 Qwen3 模型微调平台，包含完整的数据处理、训练管理和 Web 界面。

> 📍 **项目路径**: `/Users/bytedance/code/learn/all4you`
> 🌏 **国内优化**: 集成 ModelScope，下载速度提升 5-10 倍
> 🚀 **推荐模型**: Qwen3-0.6B (快速实验) / Qwen3-4B (生产应用)
> 📖 **详细文档**: [ModelScope 指南](MODELSCOPE_GUIDE.md) | [快速开始](QUICKSTART.md)

## 功能特性

- ✨ **多种微调方法**: SFT、LoRA、QLoRA、DPO、GRPO
- 🚀 **高效训练**: 集成 Unsloth 加速、FlashAttention-2
- 💾 **灵活数据处理**: 支持 JSON、CSV、JSONL 等多种格式
- 🌐 **Web 界面**: 实时训练监控、模型管理、数据预览
- 🎯 **开箱即用**: 预设多个训练配置模板
- 📊 **完整日志**: 详细的训练日志和性能指标
- 🇨🇳 **ModelScope**: 国内用户下载模型快 5-10 倍
- 💽 **智能缓存**: 自动管理模型缓存，节省磁盘空间

## 项目结构

```
all4you/                    # 项目根目录
├── backend/                # 后端服务
│   ├── api/               # API 路由（数据、训练、模型、配置）
│   ├── core/              # 核心逻辑（数据处理、训练引擎、模型管理）
│   ├── models/            # 数据模型
│   └── app.py             # FastAPI 应用
├── frontend/              # Vue3 前端
│   └── src/              # 源代码（页面、路由）
├── examples/              # 示例数据
├── MODELSCOPE_GUIDE.md    # ModelScope 完整指南
├── QUICKSTART.md          # 快速开始指南
├── setup.sh / setup.bat   # 一键安装脚本
└── requirements.txt       # Python 依赖
```

## 快速开始

### 环境需求

- Python 3.10+
- CUDA 11.8 或更高版本（用于 GPU）
- 至少 20GB 空闲磁盘空间
- Node.js 16+ (可选，用于前端)

### 一键安装

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

**Windows:**
```bash
setup.bat
```

### 手动安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt

# (可选) 安装 Unsloth 以加速训练
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
```

### 启动服务

```bash
# 启动后端
python backend/app.py

# 在另一个终端启动前端（可选）
cd frontend
npm install
npm run dev
```

访问 http://localhost:8000/docs 查看 API 文档，或访问 http://localhost:5173 使用 Web 界面。

## 配置说明

训练配置使用 YAML 格式，位于 `configs/` 目录。参考 `configs/default.yaml` 了解所有可用选项。

## 数据格式

支持以下数据格式：

### JSON 格式
```json
[
  {
    "instruction": "翻译成中文",
    "input": "Hello",
    "output": "你好"
  }
]
```

### JSONL 格式
```json
{"instruction": "翻译成中文", "input": "Hello", "output": "你好"}
{"instruction": "翻译成中文", "input": "World", "output": "世界"}
```

### CSV 格式
```csv
instruction,input,output
翻译成中文,Hello,你好
翻译成中文,World,世界
```

## API 文档

- POST `/api/train/start` - 启动训练任务
- GET `/api/train/status/{task_id}` - 获取训练状态
- POST `/api/data/upload` - 上传数据文件
- GET `/api/data/list` - 列出数据文件
- POST `/api/config/validate` - 验证配置文件

## 许可证

MIT
