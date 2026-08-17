#!/bin/bash
# build.sh - Complete build script for Render

echo "=========================================="
echo "Building SakaFundi for Render..."
echo "=========================================="

# Install system dependencies for Pillow AND PostgreSQL
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

cd src

# Create logs directory
mkdir -p logs
touch logs/django.log

# Show environment
echo "=========================================="
echo "Environment Variables:"
echo "DJANGO_ENV: $DJANGO_ENV"
echo "DATABASE_URL: ${DATABASE_URL:0:50}..."
echo "=========================================="

# Upgrade pip and install build tools
echo "Upgrading pip and installing build tools..."
python3 -m pip install --upgrade pip setuptools wheel

# Install django-redis FIRST
echo "Installing django-redis..."
python3 -m pip install --retries 5 --timeout 30 django-redis==5.4.0 redis hiredis

# Install psycopg2-binary SECOND (critical for PostgreSQL)
echo "Installing psycopg2-binary..."
python3 -m pip install --no-cache-dir --force-reinstall psycopg2-binary==2.9.9

# Verify psycopg2 installation immediately
echo "Verifying psycopg2 installation..."
python3 -c "import psycopg2; print('✅ psycopg2 installed successfully! Version:', psycopg2.__version__)" || {
    echo "❌ psycopg2 installation failed! Retrying with different approach..."
    python3 -m pip install --no-binary :all: psycopg2==2.9.9
}

# Install the rest of requirements
echo "Installing all requirements..."
python3 -m pip install --retries 10 --timeout 60 -r requirements.txt

# Final verification of critical packages
echo "Final verification of critical packages..."
python3 -c "import django_redis; print('✅ django_redis installed')"
python3 -c "import psycopg2; print('✅ psycopg2 installed')"
python3 -c "import django; print('✅ Django installed')"

# Show database settings
echo "=========================================="
echo "Database Configuration:"
python3 -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
from django.conf import settings
print(f'DATABASE ENGINE: {settings.DATABASES[\"default\"][\"ENGINE\"]}')
print(f'DATABASE NAME: {settings.DATABASES[\"default\"][\"NAME\"]}')
"
echo "=========================================="

# Run migrations
echo "Running migrations..."
python3 manage.py makemigrations
python3 manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python3 manage.py collectstatic --noinput

echo "=========================================="
echo "Build complete! ✅"
echo "=========================================="