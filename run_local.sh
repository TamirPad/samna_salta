#!/usr/bin/env bash

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Run the bot using Poetry
poetry run python main.py 