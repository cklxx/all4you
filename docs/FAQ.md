# 常见问题解答 (FAQ)

## 关于 HF_TOKEN (Hugging Face Token)

### ❓ 为什么需要 HF_TOKEN？

HF_TOKEN 是 Hugging Face 的访问令牌，用于：

1. **访问门控模型（Gated Models）**
   - 某些模型需要先同意许可协议才能下载
   - 例如：Meta 的 LLaMA 系列、某些商业模型

2. **避免下载速率限制**
   - 匿名用户可能遇到下载速度限制
   - 认证用户享有更高的带宽和优先级

3. **访问私有模型**
   - 如果你有私有训练的模型存储在 Hugging Face

### ❓ 没有 HF_TOKEN 会怎么样？

**好消息：对于 Qwen3 模型，HF_TOKEN 是可选的！** ✅

#### 场景 1：使用 Qwen3 公开模型（推荐）

```bash
# 不需要 HF_TOKEN，可以直接使用
# Qwen3 系列都是公开模型，无需认证
```

**影响**：
- ✅ 可以正常下载和使用所有 Qwen3 模型
- ✅ 可以正常训练和推理
- ⚠️  下载速度可能略慢（但国内用户使用 ModelScope 更快）

#### 场景 2：使用门控模型（如 LLaMA）

```bash
# 需要 HF_TOKEN
# 否则会报错：401 Unauthorized
```

**影响**：
- ❌ 无法下载需要认证的模型
- ❌ 会收到 HTTP 401 错误

#### 场景 3：高频下载

**影响**：
- ⚠️  可能遇到速率限制
- ⚠️  下载可能被暂时阻止

### 🔧 如何获取 HF_TOKEN？

1. **访问 Hugging Face**
   - 打开 https://huggingface.co/settings/tokens

2. **创建 Token**
   - 点击 "New token"
   - 选择 "Read" 权限（下载模型）
   - 或选择 "Write" 权限（如需上传模型）

3. **复制 Token**
   - 格式类似：`hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

4. **配置到项目**
   ```bash
   # 编辑 .env 文件
   HF_TOKEN=hf_your_actual_token_here
   ```

### 🌏 国内用户建议

如果你在国内，**强烈建议使用 ModelScope 而非 Hugging Face**：

#### 优势对比

| 特性 | ModelScope | Hugging Face |
|-----|-----------|--------------|
| **国内速度** | ⚡ 极快（5-10倍） | 🐌 很慢 |
| **需要 Token** | ❌ 不需要 | ⚠️  某些模型需要 |
| **模型覆盖** | ✅ 所有 Qwen 模型 | ✅ 全球所有模型 |
| **稳定性** | ✅ 高 | ⚠️  可能被墙 |

#### 配置方式

```bash
# .env 文件
USE_MODELSCOPE=True  # 启用 ModelScope（默认已开启）
```

**无需任何 Token！** ModelScope 上的 Qwen 模型完全公开，下载飞快。

### 📋 使用示例

#### 示例 1：不需要 Token（推荐配置）

```bash
# .env 文件
USE_MODELSCOPE=True
# HF_TOKEN=  # 留空即可

# 使用 Qwen3 模型
DEFAULT_MODEL=Qwen/Qwen3-4B
```

**结果**：
- ✅ 从 ModelScope 快速下载
- ✅ 无需任何认证
- ✅ 国内速度极快

#### 示例 2：需要 Token（访问特殊模型）

```bash
# .env 文件
USE_MODELSCOPE=False
HF_TOKEN=hf_xxxxxxxxxxxxx

# 使用门控模型（如 LLaMA）
DEFAULT_MODEL=meta-llama/Llama-2-7b-hf
```

**结果**：
- ✅ 可以访问门控模型
- ⚠️  需要先在 Hugging Face 网站同意许可协议

### 🔍 常见错误

#### 错误 1：401 Unauthorized

```
HTTPError: 401 Client Error: Unauthorized for url
```

**原因**：尝试访问门控模型但未提供 Token

**解决方案**：
1. 如果是 Qwen3 模型：设置 `USE_MODELSCOPE=True`
2. 如果是其他门控模型：配置正确的 `HF_TOKEN`

#### 错误 2：下载速度慢

**原因**：从 Hugging Face 直接下载（国内网络慢）

**解决方案**：
```bash
# 启用 ModelScope
USE_MODELSCOPE=True
```

#### 错误 3：模型找不到

```
OSError: Can't load config for 'Qwen/Qwen3-4B'
```

**原因**：网络连接问题或模型名称错误

**解决方案**：
1. 检查网络连接
2. 确认模型名称正确
3. 尝试切换到 ModelScope

### 💡 最佳实践

#### 推荐配置（国内用户）

```bash
# .env 文件
USE_MODELSCOPE=True
DEFAULT_MODEL=Qwen/Qwen3-4B
# HF_TOKEN=  # 不需要，留空即可
```

**优点**：
- 🚀 速度最快
- 🔓 无需认证
- 💯 完全免费

#### 备用配置（国外用户）

```bash
# .env 文件
USE_MODELSCOPE=False
DEFAULT_MODEL=Qwen/Qwen3-4B
HF_TOKEN=hf_xxxxxxxxxxxxx  # 可选，提升速度
```

### 🛠️ 代码中的使用

项目在以下位置使用 HF_TOKEN：

1. **core/trainer.py** - 加载模型和 tokenizer 时
2. **core/model_manager.py** - 下载和缓存模型时

**代码逻辑**：
```python
token = os.getenv("HF_TOKEN")  # 如果未设置，返回 None
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    token=token  # None 表示匿名访问
)
```

**重要**：即使 `token=None`，transformers 仍然可以下载公开模型！

### 📚 相关文档

- [Hugging Face Token 文档](https://huggingface.co/docs/hub/security-tokens)
- [ModelScope 使用指南](integrations/modelscope.md)
- [项目快速开始](../README.md#快速开始)

---

## 总结

**对于大多数用户（使用 Qwen3 模型）**：
- ✅ **不需要** HF_TOKEN
- ✅ 使用 ModelScope 即可（默认配置）
- ✅ 速度快、免费、无需认证

**只有在以下情况需要 HF_TOKEN**：
- 访问门控模型（如 LLaMA）
- 访问私有模型
- 需要特殊权限的场景

**国内用户务必使用 ModelScope，完全不需要担心 Token 问题！** 🚀
