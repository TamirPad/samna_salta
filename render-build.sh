#!/usr/bin/env bash
# exit on error
set -o errexit

# Print Python version for debugging
echo "Python version being used:"
python --version

# Check if we're using Python 3.13 and warn
if python --version | grep -q "3.13"; then
    echo "WARNING: Python 3.13 detected, this may cause compatibility issues with python-telegram-bot"
    echo "Recommended: Use Python 3.11 or 3.12"
fi

# Install Poetry if not available
if ! command -v poetry &> /dev/null; then
    echo "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

# Configure Poetry
poetry config virtualenvs.create false

# Install dependencies using Poetry
echo "Installing dependencies with Poetry..."
poetry install

# Create data directory if it doesn't exist
mkdir -p data

# Set environment to production
export ENVIRONMENT=production

echo "Build completed successfully!" 