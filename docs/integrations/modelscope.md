# ModelScope 集成指南

ModelScope（魔搭）是阿里巴巴推出的模型社区平台，为国内用户提供快速、稳定的模型下载服务。Qwen3 Fine-tuner 默认启用 ModelScope 支持，本指南介绍其优势、配置方式与典型用法。

## 1. 为什么选择 ModelScope？

| 指标 | Hugging Face | ModelScope |
| --- | --- | --- |
| 国内访问速度 | 较慢，需要代理 | 快 5-10 倍，无需代理 |
| 网络稳定性 | 依赖跨境网络 | 基于阿里云基础设施 |
| 模型镜像 | ✅ 完整 | ✅ 与 Hugging Face 同步 |
| 下载速度 | 1-5 MB/s | 10-50 MB/s |

## 2. 快速开始

### 2.1 默认行为

- 项目默认使用 ModelScope 作为模型下载源
- 无需额外设置即可在国内网络环境中使用

### 2.2 自定义配置

通过 `.env` 文件管理开关与缓存目录：

```bash
# 启用或禁用 ModelScope（默认 True）
USE_MODELSCOPE=True

# 指定模型缓存目录（可选）
MODEL_CACHE_DIR=/path/to/cache
```

## 3. 推荐模型

| 场景 | 配置 | 特性 |
| --- | --- | --- |
| 快速实验 | `model_name: Qwen/Qwen3-0.6B` | 600M 参数，显存需求低，下载 ~1.2GB |
| 通用生产（推荐） | `model_name: Qwen/Qwen3-4B` | 性能均衡，显存 ~12GB（QLoRA） |
| 高性能 | `model_name: Qwen/Qwen3-7B-Instruct`
`model_name: Qwen/Qwen3-14B-Instruct` | 更高指标，需更多显存与下载时间 |

## 4. 常用操作

### 4.1 Web 界面

1. 打开 http://localhost:5173
2. 进入 **Models** 页面
3. 选择带有「推荐」标记的模型
4. 点击 **Download** 进行预下载或更新
5. 在 **Cache** 标签页管理缓存记录

### 4.2 REST API

```bash
# 下载模型
curl -X POST "http://localhost:8000/api/models/download?model_name=Qwen/Qwen3-0.6B"

# 强制重新下载
curl -X POST "http://localhost:8000/api/models/download?model_name=Qwen/Qwen3-0.6B&force=true"

# 查看缓存列表
curl "http://localhost:8000/api/models/cache/list"

# 删除指定缓存
curl -X DELETE "http://localhost:8000/api/models/cache/Qwen_Qwen3-0.6B"

# 清空所有缓存
curl -X DELETE "http://localhost:8000/api/models/cache/all"
```

### 4.3 Python API

```python
from backend.core.model_manager import get_model_manager

# 创建模型管理器，默认启用 ModelScope
manager = get_model_manager(use_modelscope=True)

# 下载并缓存模型
cache_path = manager.ensure_model_cached("Qwen/Qwen3-0.6B")
print(f"Model cached at: {cache_path}")

# 加载模型与分词器
model, tokenizer = manager.load_model_and_tokenizer("Qwen/Qwen3-4B")

# 列出已缓存模型
for item in manager.list_cached_models():
    print(f"{item['model_name']}: {item['size'] / 1024**3:.2f} GB")

# 清理缓存
manager.evict_model("Qwen/Qwen3-0.6B")
```

## 5. 常见问题

- **如何确认当前下载源？** 查看 `USE_MODELSCOPE` 环境变量或检查后端日志中的下载 URL。
- **如何迁移已有缓存？** 将旧的缓存目录移动到新的 `MODEL_CACHE_DIR`，并保持目录层级不变。
- **下载失败怎么办？** 检查网络连通性、确保具备 ModelScope 访问权限，并重试或切换至 Hugging Face。

> 了解更多部署、诊断与测试流程，请参阅 [开发与测试手册](../development.md)。
