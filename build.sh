#!/bin/bash
# build.sh - Complete build script for Render

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
    python3-dev \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Navigate to src
cd src

# Create logs directory
mkdir -p logs
touch logs/django.log

# Show Python version
echo "Python version:"
python3 --version

# Upgrade pip and install build tools
echo "Upgrading pip and installing build tools..."
python3 -m pip install --upgrade pip setuptools wheel

# Install django-redis FIRST
echo "Installing django-redis..."
python3 -m pip install --retries 5 --timeout 30 django-redis==5.4.0 redis hiredis

# Install psycopg2-binary SECOND
echo "Installing psycopg2-binary..."
python3 -m pip install --no-cache-dir psycopg2-binary==2.9.9

# Verify psycopg2 installation
echo "Verifying psycopg2 installation..."
python3 -c "import psycopg2; print('✅ psycopg2 installed successfully!')" || {
    echo "❌ psycopg2 installation failed! Trying alternative..."
    python3 -m pip install --no-binary :all: psycopg2==2.9.9
}

# Install the rest of requirements
echo "Installing all requirements..."
python3 -m pip install --retries 10 --timeout 60 -r requirements.txt

# Final verification
echo "Final verification..."
python3 -c "import django_redis; print('✅ django_redis installed')"
python3 -c "import psycopg2; print('✅ psycopg2 installed')"

# Run Django commands
echo "Running Django commands..."
python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput

echo "=========================================="
echo "Build complete! ✅"
echo "=========================================="