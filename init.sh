#!/bin/bash

# All4You - 一键初始化环境脚本 (使用 uv)

set -e  # 遇到错误立即退出

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 开始初始化 All4You 环境..."
echo ""

# 检查 Python 版本
echo "📋 检查 Python 版本..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3，请先安装 Python 3.8+"
    exit 1
fi

python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python 版本: $python_version"
echo ""

# 检查并安装 uv
echo "📦 检查 uv 包管理器..."
if ! command -v uv &> /dev/null; then
    echo "⚠️  未检测到 uv，正在安装..."

    # 尝试使用官方安装脚本
    if command -v curl &> /dev/null; then
        echo "使用 curl 安装 uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh

        # 将 uv 添加到当前会话的 PATH
        export PATH="$HOME/.cargo/bin:$PATH"

        # 验证安装
        if command -v uv &> /dev/null; then
            echo "✅ uv 安装成功"
        else
            echo "⚠️  uv 安装后未在 PATH 中找到，尝试使用 pip 安装..."
            pip3 install uv
        fi
    else
        echo "未找到 curl，使用 pip 安装 uv..."
        pip3 install uv
    fi

    # 再次检查
    if ! command -v uv &> /dev/null; then
        echo "❌ 错误: uv 安装失败，请手动安装: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
else
    echo "✅ uv 已安装 ($(uv --version))"
fi
echo ""

# 创建或复用虚拟环境
echo "🔧 设置虚拟环境..."
if [ -d ".venv" ]; then
    echo "✅ 检测到现有虚拟环境 (.venv)，将复用现有环境"
elif [ -d "venv" ]; then
    echo "✅ 检测到现有虚拟环境 (venv)，将复用现有环境"
    # 为了统一，我们还是创建 .venv，但会提示用户
    echo "ℹ️  建议使用 .venv 作为虚拟环境目录（uv 默认），正在创建 .venv..."
    uv venv .venv
else
    echo "创建新的虚拟环境 (.venv)..."
    uv venv .venv
    echo "✅ 虚拟环境创建成功"
fi
echo ""

# 激活虚拟环境
echo "⚡ 激活虚拟环境..."
source .venv/bin/activate

# 安装依赖
echo "📥 安装项目依赖..."
echo "这可能需要几分钟时间，请耐心等待..."
echo ""

if [ -f "requirements.txt" ]; then
    uv pip install -r requirements.txt
    echo "✅ 依赖安装完成"
else
    echo "⚠️  未找到 requirements.txt 文件"
fi
echo ""

# 可选: 安装 Unsloth
echo "🔥 Unsloth 可以显著加速训练过程"
read -p "是否安装 Unsloth? (y/n) [默认: n]: " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "正在安装 Unsloth..."
    uv pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
    echo "✅ Unsloth 安装完成"
else
    echo "⏭️  跳过 Unsloth 安装"
fi
echo ""

# 创建 .env 文件
echo "⚙️  配置环境变量..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ 已从 .env.example 创建 .env 文件"
        echo "⚠️  请根据需要编辑 .env 文件（如添加 Hugging Face Token）"
    else
        echo "⚠️  未找到 .env.example 文件，跳过 .env 创建"
    fi
else
    echo "✅ .env 文件已存在"
fi
echo ""

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p backend/data backend/outputs backend/logs backend/configs
echo "✅ 目录创建完成"
echo ""

# 测试导入
echo "🧪 测试 Python 模块导入..."
if [ -f "test_imports.py" ]; then
    python test_imports.py
    test_result=$?
else
    echo "⚠️  未找到 test_imports.py，跳过导入测试"
    test_result=0
fi
echo ""

# 完成提示
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $test_result -eq 0 ]; then
    echo "✅ 环境初始化完成！"
else
    echo "⚠️  环境初始化完成（部分模块导入失败）"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 后续步骤:"
echo ""
echo "  1. 激活虚拟环境:"
echo "     source .venv/bin/activate"
echo ""
echo "  2. （可选）编辑 .env 文件配置:"
echo "     - 添加 Hugging Face Token"
echo "     - 调整模型和训练参数"
echo ""
echo "  3. 启动应用:"
echo "     ./scripts/start.sh        # 生产模式"
echo "     ./scripts/dev.sh          # 开发模式"
echo ""
echo "  4. 访问 API 文档:"
echo "     http://localhost:8000/docs"
echo ""
echo "💡 提示: uv 的优势"
echo "   - 极快的依赖解析和安装速度（比 pip 快 10-100 倍）"
echo "   - 自动管理 Python 版本和虚拟环境"
echo "   - 确定性的依赖解析，避免版本冲突"
echo ""
echo "📚 更多信息请查看 README.md"
echo ""
