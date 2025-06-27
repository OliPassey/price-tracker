#!/bin/bash

# Build script for Price Tracker Docker container

set -e

# Configuration
IMAGE_NAME="price-tracker"
TAG="${1:-latest}"
REGISTRY="${2:-your-registry.com}"  # Replace with your actual registry

echo "Building Price Tracker Docker image..."

# Build the Docker image
docker build -t "${IMAGE_NAME}:${TAG}" .

# Tag for registry if provided
if [ "$REGISTRY" != "your-registry.com" ]; then
    docker tag "${IMAGE_NAME}:${TAG}" "${REGISTRY}/${IMAGE_NAME}:${TAG}"
    echo "Tagged image as ${REGISTRY}/${IMAGE_NAME}:${TAG}"
fi

echo "Build completed successfully!"
echo "Image: ${IMAGE_NAME}:${TAG}"

# Display image info
docker images | grep "${IMAGE_NAME}"

echo ""
echo "To run locally:"
echo "  docker run -p 5000:5000 ${IMAGE_NAME}:${TAG}"
echo ""
echo "To push to registry:"
echo "  docker push ${REGISTRY}/${IMAGE_NAME}:${TAG}"
echo ""
echo "To run with docker-compose:"
echo "  docker-compose up -d"
