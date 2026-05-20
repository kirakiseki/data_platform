#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORIG_DIR="$(pwd)"

echo "=== Deploying Frontend ==="
cd "$SCRIPT_DIR/frontend"
./deploy.sh

echo "=== Deploying Backend ==="
cd "$SCRIPT_DIR/backend"
./deploy.sh

cd "$ORIG_DIR"
echo "=== Deployment Complete ==="
