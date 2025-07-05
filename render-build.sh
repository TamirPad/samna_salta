#!/usr/bin/env bash
# exit on error
set -o errexit

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

# Upgrade pip and install poetry
echo "Installing/updating dependencies..."
pip install --upgrade pip
pip install poetry

# Install project dependencies
poetry install --no-interaction --no-ansi

# Create data directory if it doesn't exist
mkdir -p data

echo "Build completed successfully!" 