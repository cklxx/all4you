# 开发与测试手册

本文档介绍在本地搭建开发环境、运行测试以及常见诊断方法，帮助你高效迭代 Qwen3 Fine-tuner。

## 1. 基础环境

- **Python**：3.10 及以上版本
- **Node.js**：16 及以上（前端开发）
- **数据库**：项目默认使用 SQLite，无需额外配置
- **GPU 驱动**：建议使用 CUDA 11.8+，以获得最佳训练性能

> 建议使用 `python -m venv venv` 创建虚拟环境，并通过 `pip install -r requirements.txt` 安装依赖。

## 2. 代码结构

```
backend/
  api/           # FastAPI 路由（数据、训练、模型、配置）
  core/          # 数据处理、训练调度、模型管理
  models/        # Pydantic 数据模型
frontend/
  src/           # Vue3 页面、组件与路由
```

更多文件说明参见 [快速上手指南](getting-started.md)。

## 3. 后端开发流程

1. 启动开发服务器：`python backend/app.py`
2. 浏览 `http://localhost:8000/docs` 验证 API 是否可用
3. 推荐通过 `uvicorn backend.app:app --reload` 支持热重载
4. 若新增依赖，请同步更新 `requirements.txt`

### 3.1 代码风格

- 使用 `ruff` 或 `flake8` 等工具保持 PEP 8 风格（可选）
- 避免在模块级别进行重型导入，必要时延迟加载（尤其是模型相关依赖）
- 数据库会话需使用上下文管理，后台任务内需自行创建会话

### 3.2 后端测试

- **依赖检测**：`python test_imports.py`
- **单元/集成测试**：在 `backend/tests/` 目录中新增 pytest 用例（如需）

## 4. 前端开发流程

1. 安装依赖：`cd frontend && npm install`
2. 启动开发服务器：`npm run dev`
3. 访问 `http://localhost:5173` 查看页面效果
4. 提交前执行 `npm run build` 确认可正常构建

### 4.1 代码风格

- 使用 ESLint + Prettier（已在 `package.json` 中配置）
- Vue 组件优先采用 `<script setup>` 语法
- 统一使用 Composition API 与 TypeScript 类型注解（如有）

## 5. 数据与模型管理

- 数据文件默认存储于 `data/`（可在配置中修改）
- 上传数据前建议在本地进行格式校验（JSON/CSV/JSONL）
- 模型缓存目录可通过环境变量 `MODEL_CACHE_DIR` 设置
- 使用 ModelScope 时可参考 [ModelScope 集成指南](integrations/modelscope.md)

## 6. 常见诊断

| 场景 | 排查建议 |
| --- | --- |
| 导入报错 | 确认虚拟环境已激活，执行 `python test_imports.py` 检查依赖 |
| 训练失败 | 查看 `backend/logs/` 中的日志，检查配置或显存占用 |
| 前端接口报错 | 打开浏览器控制台，检查网络请求与后端响应 |
| 进度显示异常 | 确认后端训练任务是否正确记录 `progress_percentage` |

## 7. 提交流程

1. 确认 `git status` 干净且变更完整
2. 运行 `python test_imports.py` 与 `npm run build`
3. 更新相关文档并确保引用路径正确
4. 提交 PR 时描述影响面、测试结果与后续风险

如需了解历史修复与阶段总结，可访问 [项目报告归档](reports/README.md)。
