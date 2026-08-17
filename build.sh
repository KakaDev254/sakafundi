#!/bin/bash
# build.sh - Complete build script for Render

echo "=========================================="
echo "Building SakaFundi for Render..."
echo "=========================================="

# ============================================================
# 1. Install System Dependencies (for Pillow)
# ============================================================
echo "Installing system dependencies..."
apt-get update && apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    libwebp-dev \
    python3-dev

# ============================================================
# 2. Upgrade pip
# ============================================================
echo "Upgrading pip..."
pip install --upgrade pip

# ============================================================
# 3. Install Python Dependencies
# ============================================================
echo "Installing Python dependencies..."
# Navigate to src where requirements.txt is
cd src
pip install --retries 5 --timeout 30 -r requirements.txt

# ============================================================
# 4. Django Commands
# ============================================================
echo "Running Django commands..."

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate --noinput

# ============================================================
# 5. Create Superuser (Optional - skip if not needed)
# ============================================================
# echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" | python manage.py shell

echo "=========================================="
echo "Build complete! ✅"
echo "=========================================="