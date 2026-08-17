#!/bin/bash
# build.sh

echo "=========================================="
echo "Building SakaFundi for Render..."
echo "=========================================="

# Install system dependencies
echo "Installing system dependencies..."
apt-get update
apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    libwebp-dev \
    python3-dev

cd src

# Create logs directory (just in case)
mkdir -p logs
touch logs/django.log

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install django-redis FIRST
echo "Installing django-redis..."
python -m pip install --retries 5 --timeout 30 django-redis==5.4.0 redis hiredis

# Install the rest of requirements
echo "Installing all requirements..."
python -m pip install --retries 10 --timeout 60 -r requirements.txt

# Run Django commands
echo "Running Django commands..."
python manage.py collectstatic --noinput
python manage.py migrate --noinput

echo "=========================================="
echo "Build complete! ✅"
echo "=========================================="