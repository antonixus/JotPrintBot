#!/bin/bash

echo "Pulling latest changes from GitHub..."
git pull

if [ -z "$VIRTUAL_ENV" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Virtual environment already activated."
fi

echo "Restarting bot service..."
systemctl restart bot

# Проверка статуса (опционально)
systemctl status bot --no-pager

echo "Deployment complete!"