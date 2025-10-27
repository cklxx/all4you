# ModelScope 支持指南

## 什么是 ModelScope？

[ModelScope（魔搭）](https://modelscope.cn)是阿里巴巴推出的模型社区平台，为国内用户提供快速、稳定的模型下载服务。

## 为什么使用 ModelScope？

### 优势
- ✅ **速度更快**: 国内服务器，下载速度快 5-10 倍
- ✅ **无需科学上网**: 直接访问，无需代理
- ✅ **稳定可靠**: 阿里云基础设施支持
- ✅ **完整镜像**: 同步 Hugging Face 最新模型

### 对比

| 特性 | Hugging Face | ModelScope |
|------|--------------|------------|
| 国内访问速度 | 较慢 | 快 |
| 需要代理 | 部分需要 | 不需要 |
| 模型完整性 | ✅ 完整 | ✅ 完整 |
| 下载速度 | 1-5 MB/s | 10-50 MB/s |

## 快速开始

### 1. 自动配置（推荐）

Qwen3 Fine-tuner **默认启用 ModelScope**，无需额外配置。

### 2. 手动配置

如果需要调整，编辑 `.env` 文件：

```bash
# 启用 ModelScope（默认已启用）
USE_MODELSCOPE=True

# 禁用 ModelScope，使用 Hugging Face
USE_MODELSCOPE=False

# 自定义缓存目录（可选）
MODEL_CACHE_DIR=/path/to/your/cache
```

## 推荐的模型配置

### 快速实验 - 0.6B 模型

**推荐场景**: 快速验证、原型开发、资源受限环境

```yaml
model_name: Qwen/Qwen3-0.6B
```

**特点**:
- 参数量: 600M
- 显存需求: 4GB (QLoRA)
- 训练速度: 极快
- 下载大小: ~1.2GB
- 预计下载时间: 1-3 分钟

**性能**:
- 适合简单任务
- 推理速度快
- 部署成本低

### 通用场景 - 4B 模型 ⭐

**推荐场景**: 大多数生产应用、平衡性能和效率

```yaml
model_name: Qwen/Qwen3-4B
```

**特点**:
- 参数量: 4B
- 显存需求: 12GB (QLoRA)
- 训练速度: 快
- 下载大小: ~8GB
- 预计下载时间: 5-10 分钟

**性能**:
- 性能优秀
- 速度较快
- 性价比最高 ⭐

### 高性能 - 7B/14B 模型

**推荐场景**: 对性能要求高的场景

```yaml
# 7B 模型
model_name: Qwen/Qwen3-7B-Instruct

# 14B 模型
model_name: Qwen/Qwen3-14B-Instruct
```

## 使用方法

### 通过 Web 界面

1. 打开 http://localhost:5173
2. 进入 **Models** 页面
3. 选择带 **【推荐】** 标记的模型
4. 点击 **Download** 预下载模型
5. 查看 **Cache** 标签管理已缓存模型

### 通过 API

#### 下载模型

```bash
# 下载 0.6B 模型
curl -X POST "http://localhost:8000/api/models/download?model_name=Qwen/Qwen3-0.6B"

# 下载 4B 模型
curl -X POST "http://localhost:8000/api/models/download?model_name=Qwen/Qwen3-4B"

# 强制重新下载
curl -X POST "http://localhost:8000/api/models/download?model_name=Qwen/Qwen3-0.6B&force=true"
```

#### 查看已缓存模型

```bash
curl "http://localhost:8000/api/models/cache/list"
```

#### 清除缓存

```bash
# 清除特定模型
curl -X DELETE "http://localhost:8000/api/models/cache/Qwen_Qwen3-0.6B"

# 清除所有缓存
curl -X DELETE "http://localhost:8000/api/models/cache/all"
```

### 通过 Python

```python
from core.model_manager import get_model_manager

# 获取模型管理器
manager = get_model_manager(use_modelscope=True)

# 下载并缓存模型
cache_path = manager.ensure_model_cached("Qwen/Qwen3-0.6B")
print(f"Model cached at: {cache_path}")

# 加载模型和分词器
model, tokenizer = manager.load_model_and_tokenizer("Qwen/Qwen3-4B")

# 查看缓存
cached_models = manager.list_cached_models()
for m in cached_models:
    print(f"{m['model_name']}: {m['size'] / 1024**3:.2f} GB")

# 清除缓存
manager.clear_cache("Qwen/Qwen3-0.6B")
```

## 缓存管理

### 缓存位置

默认缓存目录：`~/.cache/qwen3-finetuner/models`

自定义缓存：
```bash
# 在 .env 文件中设置
MODEL_CACHE_DIR=/data/models
```

### 缓存结构

```
~/.cache/qwen3-finetuner/models/
├── Qwen--Qwen3-0.6B/
│   ├── config.json
│   ├── pytorch_model.bin
│   └── tokenizer.json
├── Qwen--Qwen3-4B/
│   └── ...
└── Qwen--Qwen3-7B-Instruct/
    └── ...
```

### 磁盘空间管理

| 模型 | 磁盘占用 |
|------|---------|
| 0.6B | ~1.2 GB |
| 3B | ~6 GB |
| 4B | ~8 GB |
| 7B | ~14 GB |
| 14B | ~28 GB |

**建议**:
- 预留 20GB+ 空间用于缓存
- 定期清理不用的模型
- 使用 SSD 以提升加载速度

## 故障排除

### 问题 1: ModelScope 安装失败

```bash
# 手动安装
pip install modelscope==1.11.0
```

### 问题 2: 下载速度慢

**解决方案**:
1. 检查 `USE_MODELSCOPE=True` 是否生效
2. 尝试更换网络环境
3. 检查防火墙设置

### 问题 3: 缓存空间不足

```bash
# 查看缓存占用
du -sh ~/.cache/qwen3-finetuner/models

# 清除旧模型
curl -X DELETE "http://localhost:8000/api/models/cache/Qwen_Qwen3-7B"

# 或手动删除
rm -rf ~/.cache/qwen3-finetuner/models/Qwen--Qwen3-7B
```

### 问题 4: 下载中断

ModelScope 和 Hugging Face 都支持断点续传，重新下载会从断点继续。

## 最佳实践

### 1. 预下载模型

在开始训练前预下载模型，避免训练时等待：

```bash
# 下载推荐的模型
python -c "
from core.model_manager import get_model_manager
manager = get_model_manager()
manager.ensure_model_cached('Qwen/Qwen3-0.6B')
manager.ensure_model_cached('Qwen/Qwen3-4B')
"
```

### 2. 选择合适的模型

| 场景 | 推荐模型 | 理由 |
|------|---------|------|
| 快速验证 | 0.6B | 下载快、训练快 |
| 生产应用 | 4B | 性能好、效率高 |
| 高性能需求 | 7B/14B | 最佳性能 |

### 3. 缓存管理策略

```python
# 定期检查缓存
manager = get_model_manager()
cached = manager.list_cached_models()

# 清理大型模型，保留小模型
for model in cached:
    if model['size'] > 20 * 1024**3:  # 大于 20GB
        manager.clear_cache(model['model_name'])
```

### 4. 网络环境选择

- **国内用户**: 启用 ModelScope（默认）
- **海外用户**: 禁用 ModelScope，使用 Hugging Face
- **企业内网**: 配置自定义缓存目录

## 性能对比

### 下载速度对比（国内网络）

| 模型 | Hugging Face | ModelScope | 提升 |
|------|--------------|------------|------|
| 0.6B | 5-10 分钟 | 1-3 分钟 | 3-5x |
| 4B | 30-60 分钟 | 5-10 分钟 | 5-10x |
| 7B | 60-120 分钟 | 10-20 分钟 | 5-10x |

### 训练速度对比（使用 QLoRA）

| 模型 | GPU 显存 | 训练速度 (tokens/s) |
|------|----------|---------------------|
| 0.6B | 4GB | ~2000 |
| 4B | 12GB | ~500 |
| 7B | 16GB | ~300 |

## 常见问题

**Q: ModelScope 是否安全？**
A: 是的，ModelScope 是阿里巴巴官方平台，模型与 Hugging Face 完全同步。

**Q: 可以同时使用多个下载源吗？**
A: 系统会自动尝试 ModelScope，失败后回退到 Hugging Face。

**Q: 如何验证下载的模型完整性？**
A: 模型下载后会自动验证 `config.json`，确保完整性。

**Q: 缓存可以共享吗？**
A: 可以，设置相同的 `MODEL_CACHE_DIR` 即可共享缓存。

## 相关链接

- [ModelScope 官网](https://modelscope.cn)
- [Qwen 模型主页](https://modelscope.cn/organization/qwen)
- [Hugging Face 镜像](https://hf-mirror.com)

## 技术支持

遇到问题？
1. 查看日志: `backend/logs/app.log`
2. 检查缓存: `ls -lh ~/.cache/qwen3-finetuner/models`
3. 提交 Issue: [GitHub Issues](https://github.com/your-repo/issues)

---

**更新时间**: 2024-10-27
**版本**: 0.1.2
