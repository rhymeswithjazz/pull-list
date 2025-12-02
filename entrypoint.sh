#!/bin/bash

PUID=${PUID:-1000}
PGID=${PGID:-1000}

echo "Starting with UID: $PUID, GID: $PGID"

# Get or create group
GROUP_NAME=$(getent group "$PGID" | cut -d: -f1)
if [ -z "$GROUP_NAME" ]; then
    groupadd -g "$PGID" appgroup
    GROUP_NAME="appgroup"
fi

# Create user if it doesn't exist
if ! getent passwd appuser > /dev/null 2>&1; then
    useradd -u "$PUID" -g "$PGID" -m -s /bin/bash appuser
else
    # Update existing user's UID/GID if needed
    usermod -u "$PUID" -g "$PGID" appuser 2>/dev/null || true
fi

# Ensure ownership of entire app directory
chown -R appuser:"$GROUP_NAME" /app

# Run the application as appuser
exec gosu appuser uvicorn app.main:app --host 0.0.0.0 --port 8000
