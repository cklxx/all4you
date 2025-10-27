# Qwen3 Fine-tuner

一个专业的 Qwen3 模型微调平台，提供端到端的数据处理、训练编排以及现代化的 Web 界面。

> 📍 **项目路径**: `/Users/bytedance/code/learn/all4you`
> 🌏 **国内优化**: 深度集成 ModelScope，模型下载加速 5-10 倍
> 🚀 **推荐模型**: Qwen3-0.6B（快速验证） / Qwen3-4B（生产环境）

## 文档索引

| 主题 | 内容概览 |
| --- | --- |
| [快速上手](docs/getting-started.md) | 安装、启动、常见工作流、故障排除与 FAQ |
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

1. **安装依赖**：`pip install -r requirements.txt`
2. **启动后端**：`python backend/app.py`
3. **启动前端（可选）**：`cd frontend && npm install && npm run dev`
4. **访问服务**：
   - API 文档：http://localhost:8000/docs
   - Web 界面：http://localhost:5173

> 详细安装步骤与常见问题，请参见 [快速上手指南](docs/getting-started.md)。

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
├── setup.sh / setup.bat   # 一键安装脚本
└── start.sh / start.bat   # 一键启动脚本
```

## 开发与测试

- **后端依赖检查**：`python test_imports.py`
- **前端构建检查**：`cd frontend && npm run build`
- 更多开发细节、代码规范与诊断方法请参阅 [开发与测试手册](docs/development.md)。

## 许可证

本项目采用 [MIT](LICENSE) 开源协议。
