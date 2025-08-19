#!/bin/bash

# Export environment variables from .env-cvat
set -o allexport
source .env
set +o allexport

# Create local directory to persist component data
if [[ ! -d "$CVAT_COMPONENTS_DIR" ]]; then
  echo "Creating data directory at $CVAT_COMPONENTS_DIR..."
  mkdir -p "$CVAT_COMPONENTS_DIR"
fi

if [[ ! -d "$CVAT_SHARE_DIR" ]]; then
  echo "Creating data directory at $CVAT_SHARE_DIR..."
  mkdir -p "$CVAT_SHARE_DIR"
fi

# Start CVAT
docker compose \
  -f docker-compose.yml \
  up -d
