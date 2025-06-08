#!/bin/bash
set -e

echo "📦 Creating virtual environment..."
python -m venv kasdogs310-env

echo "✅ Activating virtual environment..."
source kasdogs310-env/Scripts/activate

echo "📚 Installing dependencies from requirements.txt..."
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "🎉 Setup complete!"
echo "🐍 Python version: $(python --version)"
echo "📦 Installed packages:"
pip list
