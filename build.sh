#!/bin/bash
# build.sh

echo "Building SakaFundi for Render..."

# Install dependencies
pip install -r requirements.txt

# Navigate to src
cd src

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

echo "Build complete!"