#!/bin/bash
# Deploy script to start docker-compose services on host from within a container
# Requires: Docker socket mounted at /var/run/docker.sock on host

pnpm install --frozen-lockfile
pnpm run build

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yaml"
DOCKER_SOCK="${DOCKER_SOCK:-/var/run/docker.sock}"

# Check if docker socket exists
if [ ! -S "$DOCKER_SOCK" ]; then
    echo "Error: Docker socket not found at $DOCKER_SOCK"
    echo "Please mount the host docker socket: -v /var/run/docker.sock:/var/run/docker.sock"
    exit 1
fi

# Load environment variables from .env file
ENV_FILE="$SCRIPT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# Set environment variables (fallback to .env values)
export DATAPLATFORM_DOMAIN="${DATAPLATFORM_DOMAIN:-your-domain.example.com}"
export DOCKER_HOST="unix://$DOCKER_SOCK"

# Navigate to the frontend directory and run docker-compose
cd "$SCRIPT_DIR"

echo "Deploying dataplatform-frontend..."
echo "  Compose file: $COMPOSE_FILE"
echo "  Domain: $DATAPLATFORM_DOMAIN"

# Pull and up the services
docker compose -f "$COMPOSE_FILE" down --remove-orphans
docker compose -f "$COMPOSE_FILE" up -d --build

echo ""
echo "Services started. Checking status..."
docker compose -f "$COMPOSE_FILE" ps

echo ""
echo "Waiting for services to become healthy..."

# Health check configuration
TIMEOUT=120  # seconds
INTERVAL=3   # seconds
ELAPSED=0

# Get all services with healthcheck defined
SERVICES=$(docker compose -f "$COMPOSE_FILE" ps --services --format json 2>/dev/null | grep -v '^$' || true)

while [ $ELAPSED -lt $TIMEOUT ]; do
    # Check if all services are healthy
    UNHEALTHY=""
    for service in $SERVICES; do
        STATUS=$(docker compose -f "$COMPOSE_FILE" ps "$service" --format json 2>/dev/null | grep -o '"Health":"[^"]*"' | cut -d'"' -f4 || echo "none")
        if [ "$STATUS" != "healthy" ]; then
            UNHEALTHY="$UNHEALTHY $service"
        fi
    done

    if [ -z "$UNHEALTHY" ]; then
        echo "All services are healthy!"
        break
    fi

    echo "Waiting for services to be healthy... ($ELAPSED/${TIMEOUT}s)"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo ""
    echo "WARNING: Timeout waiting for services to become healthy"
    echo "Some services may not be ready. Check status below:"
    echo ""
fi

echo ""
echo "Deployment complete!"
echo ""
echo "Service status:"
docker compose -f "$COMPOSE_FILE" ps
