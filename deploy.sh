#!/bin/bash

# Deployment script for Price Tracker

set -e

# Configuration
IMAGE_NAME="price-tracker"
TAG="${1:-latest}"
REGISTRY="${2:-your-registry.com}"  # Replace with your actual registry
CONTAINER_NAME="price-tracker"

echo "Deploying Price Tracker..."

# Pull latest image if using registry
if [ "$REGISTRY" != "your-registry.com" ]; then
    echo "Pulling latest image from registry..."
    docker pull "${REGISTRY}/${IMAGE_NAME}:${TAG}"
fi

# Stop and remove existing container if it exists
if docker ps -a | grep -q "${CONTAINER_NAME}"; then
    echo "Stopping existing container..."
    docker stop "${CONTAINER_NAME}" || true
    docker rm "${CONTAINER_NAME}" || true
fi

# Create data and logs directories if they don't exist
mkdir -p ./data ./logs

# Run the container
echo "Starting new container..."
docker run -d \
    --name "${CONTAINER_NAME}" \
    --restart unless-stopped \
    -p 5000:5000 \
    -v "$(pwd)/data:/app/data" \
    -v "$(pwd)/logs:/app/logs" \
    -v "$(pwd)/config.json:/app/config.json:ro" \
    -e FLASK_ENV=production \
    "${REGISTRY}/${IMAGE_NAME}:${TAG}"

echo "Container started successfully!"
echo "Access the application at: http://localhost:5000"
echo ""
echo "To view logs:"
echo "  docker logs -f ${CONTAINER_NAME}"
echo ""
echo "To stop the container:"
echo "  docker stop ${CONTAINER_NAME}"
