#!/usr/bin/env bash
# exit on error
set -o errexit

# Upgrade pip first to avoid compatibility issues
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Create data directory if it doesn't exist
mkdir -p data

# Set environment to production
export ENVIRONMENT=production 