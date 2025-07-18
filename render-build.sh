#!/usr/bin/env bash
# exit on error
set -o errexit

# Use Poetry's in-project virtualenv so runtime path is predictable
poetry config virtualenvs.in-project true

# Install dependencies according to lockfile
poetry install --no-interaction --no-ansi

# Ensure runtime data directory exists
mkdir -p data

# Run deployment test
echo "Running deployment test..."
python test_deployment.py

echo "Build completed successfully!" 