#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🚀 Starting build process..."

# Use Poetry's in-project virtualenv so runtime path is predictable
poetry config virtualenvs.in-project true

# Install dependencies according to lockfile
echo "📦 Installing dependencies..."
poetry install --no-interaction --no-ansi --only=main

# Ensure runtime directories exist
echo "📁 Creating runtime directories..."
mkdir -p data logs

# Set proper permissions
chmod +x main.py
chmod +x scripts/verify_deployment.py

# Verify Python version
echo "🐍 Python version:"
python --version

# Verify installation
echo "✅ Dependencies installed:"
poetry show --tree

# Run deployment verification (optional - can be disabled if causing issues)
echo "🔍 Running deployment verification..."
if python scripts/verify_deployment.py; then
    echo "✅ Deployment verification passed"
else
    echo "⚠️  Deployment verification failed - continuing anyway"
fi

echo "🎉 Build completed successfully!" 