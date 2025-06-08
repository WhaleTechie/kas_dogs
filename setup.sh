#!/bin/bash
set -e

echo "📦 Creating virtual environment..."
python -m venv kasdogs310-env

echo "✅ Activating virtual environment..."
if [ -f "kasdogs310-env/bin/activate" ]; then
    # Unix-like systems
    source kasdogs310-env/bin/activate
elif [ -f "kasdogs310-env/Scripts/activate" ]; then
    # Windows
    source kasdogs310-env/Scripts/activate
else
    echo "Unable to locate the virtual environment activation script." >&2
    exit 1
fi

echo "📚 Installing dependencies from requirements.txt..."
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "🎉 Setup complete!"
echo "🐍 Python version: $(python --version)"
echo "📦 Installed packages:"
pip list
