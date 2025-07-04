#!/usr/bin/env bash
# exit on error
set -o errexit

# Print Python version for debugging
echo "Python version being used:"
python --version

# Upgrade pip first to avoid compatibility issues
pip install --upgrade pip

# Install dependencies with verbose output
pip install -r requirements.txt --verbose

# Create data directory if it doesn't exist
mkdir -p data

# Set environment to production
export ENVIRONMENT=production

echo "Build completed successfully!" 