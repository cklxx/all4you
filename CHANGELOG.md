# Changelog

所有重要的变更都会记录在这个文件中。

## [0.1.1] - 2024-10-27

### 🐛 Bug 修复

#### 后端修复
1. **依赖问题**
   - ✅ 添加缺失的 `pydantic-settings==2.1.0` 依赖
   - ✅ 修复 `unsloth` 包的安装说明（标记为可选）
   - ✅ 更新 `bitsandbytes` 版本至 0.41.3

2. **配置管理 (`backend/core/config.py`)**
   - ✅ 升级至 Pydantic v2 API
   - ✅ 使用 `SettingsConfigDict` 替代旧的 `Config` 类
   - ✅ 使用 `@model_validator` 替代 `__init__` 方法
   - ✅ 添加 `arbitrary_types_allowed=True` 以支持 Path 类型

3. **训练 API (`backend/api/training.py`)**
   - ✅ 修复后台任务的数据库会话管理问题
   - ✅ 在后台任务中创建新的数据库会话
   - ✅ 添加 `finally` 块确保会话正确关闭
   - ✅ 移除传递已关闭会话给后台任务的错误

#### 前端修复
4. **数据管理页面 (`frontend/src/pages/DataManagement.vue`)**
   - ✅ 修复变量名冲突：`previewData` (ref) vs `previewData` (function)
   - ✅ 重命名函数为 `handlePreviewData` 避免冲突
   - ✅ 更新模板中的事件处理器引用

### ✨ 新增功能

5. **安装脚本**
   - ✅ 添加 `setup.sh` (Linux/Mac 自动安装脚本)
   - ✅ 添加 `setup.bat` (Windows 自动安装脚本)
   - ✅ 添加 `test_imports.py` (导入测试脚本)

6. **文档改进**
   - ✅ 更新 README.md 添加一键安装说明
   - ✅ 添加 CHANGELOG.md 记录变更历史
   - ✅ 改进安装和故障排除说明

### 📝 技术细节

#### Pydantic v2 迁移要点
- 旧版：`class Config` → 新版：`model_config = SettingsConfigDict(...)`
- 旧版：`__init__` → 新版：`@model_validator(mode='after')`
- 必须设置 `arbitrary_types_allowed=True` 才能使用 `Path` 类型

#### 数据库会话管理
- FastAPI 依赖注入的会话在请求结束后会关闭
- 后台任务必须创建自己的会话
- 使用 `try-except-finally` 确保会话正确关闭

#### JavaScript 命名冲突
- Vue 3 Composition API 中，ref 变量和函数不能同名
- 使用 `handle` 前缀命名事件处理函数以避免冲突

### 🔧 改进的依赖列表

```txt
# 核心框架
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0  # 新增
python-multipart==0.0.6

# 优化
bitsandbytes==0.41.3  # 版本更新
# unsloth - 标记为可选，需单独安装
```

### 🚀 使用建议

1. **首次安装**：
   ```bash
   ./setup.sh  # 或 setup.bat (Windows)
   ```

2. **测试导入**：
   ```bash
   python test_imports.py
   ```

3. **启动应用**：
   ```bash
   ./start.sh  # 或 start.bat (Windows)
   ```

### ⚠️ 已知问题

1. **Unsloth 安装**
   - Unsloth 不在标准 PyPI 上，需要从 GitHub 安装
   - Windows 支持有限，建议在 Linux/Mac 或 WSL2 中使用

2. **CUDA 依赖**
   - PyTorch 和 bitsandbytes 需要 CUDA 11.8+
   - 确保安装了正确版本的 CUDA 驱动

### 📊 测试状态

- ✅ Python 语法检查通过
- ✅ 导入测试通过
- ✅ Pydantic 配置验证通过
- ⚠️ 完整功能测试需要 GPU 环境

---

## [0.1.0] - 2024-10-27

### 🎉 初始版本

- ✅ 完整的 FastAPI 后端 (21 个 API 端点)
- ✅ Vue3 + Element Plus 前端
- ✅ 支持多种数据格式 (JSON, JSONL, CSV, TXT)
- ✅ 支持多种训练方法 (SFT, LoRA, QLoRA, DPO, GRPO)
- ✅ 集成 Unsloth、FlashAttention-2 优化
- ✅ 8 个预置 Qwen3 模型
- ✅ 4 个默认训练配置
- ✅ 完整的文档和示例数据

---

## 版本说明

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

### 版本类型
- **Major (主版本号)**: 不兼容的 API 修改
- **Minor (次版本号)**: 向下兼容的功能性新增
- **Patch (修订号)**: 向下兼容的问题修正

### 变更类型
- `Added` - 新增功能
- `Changed` - 功能变更
- `Deprecated` - 即将废弃的功能
- `Removed` - 已移除的功能
- `Fixed` - 问题修复
- `Security` - 安全性修复
# [Unreleased]

### ✨ 新增功能

- 新增 `scripts/pipeline.py` 命令行工具，可在单条命令中完成数据处理、模型微调以及自动评测，并产出结构化报告。
- 引入 `backend/core/evaluator.py`，支持使用指定评测模型（默认 `Qwen/Qwen3-4B`）对生成结果进行打分与解释。
- 集成 `backend/core/dataset_hub.py` 与 `scripts/download_dataset.py`，支持从魔搭（ModelScope）一键拉取内容理解、搜索意图、Query 解析等数据集，并通过 `--moda-*` 参数直接接入训练流水线。

### ♻️ 结构调整

- 所有 Shell/Bat 启动脚本迁移至 `scripts/` 目录，统一路径并更新 README、文档示例说明。
- 将默认基础模型调整为 `Qwen/Qwen3-4B`，并在工作流中标注 `Qwen/Qwen3-0.6B` 作为快速验证选项。

