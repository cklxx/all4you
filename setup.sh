#!/bin/bash

# Qwen3 Fine-tuner Setup Script

echo "🔧 Setting up Qwen3 Fine-tuner..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Optional: Install Unsloth
read -p "Install Unsloth for faster training? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing Unsloth..."
    pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your Hugging Face token"
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p backend/data backend/outputs backend/logs backend/configs

# Test imports
echo ""
echo "Testing imports..."
python test_imports.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Edit .env and add your Hugging Face token (optional)"
    echo "  2. Run './start.sh' to start the application"
    echo "  3. Visit http://localhost:8000/docs for API documentation"
else
    echo ""
    echo "⚠️  Setup completed with warnings"
    echo "Some imports failed, but you can try running the application"
fi
