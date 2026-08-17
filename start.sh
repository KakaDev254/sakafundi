#!/bin/bash
# start.sh

echo "Starting SakaFundi..."

# Navigate to src
cd src

# Run with Daphne (for WebSocket support)
daphne -b 0.0.0.0 -p $PORT config.asgi:application