#!/bin/bash

# Build script for all microservices
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Build mode:
# - USE_MINIKUBE_DOCKER=1 (default): build directly into Minikube's docker daemon
# - USE_MINIKUBE_DOCKER=0: build using local Docker Desktop, then (optionally) minikube image load
USE_MINIKUBE_DOCKER=${USE_MINIKUBE_DOCKER:-1}
LOAD_TO_MINIKUBE=${LOAD_TO_MINIKUBE:-1}

if [ "$USE_MINIKUBE_DOCKER" = "1" ]; then
    # Get Minikube Docker environment
    eval $(minikube docker-env)
fi

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
MINIKUBE_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
REPO_ROOT=$(cd "$MINIKUBE_DIR/../.." && pwd)

# Services to build
services=(
    "auth-service"
    "expense-service"
    "balance-service"
    # Add more services as needed
)

get_service_port() {
    case "$1" in
        "auth-service") echo "8001" ;;
        "expense-service") echo "8003" ;;
        "balance-service") echo "8004" ;;
        *) echo "8000" ;;
    esac
}

# Build each service
for service in "${services[@]}"; do
    log_info "Building $service..."
    
    cd "$REPO_ROOT/services/$service"

    SERVICE_PORT=$(get_service_port "$service")
    
    # Create Dockerfile if it doesn't exist
    if [ ! -f "Dockerfile" ]; then
        cat > Dockerfile <<EOF
FROM golang:1.21-bookworm AS builder

ARG GOPROXY=https://proxy.golang.org,direct
ARG GOSUMDB=off
ENV GOPROXY=$GOPROXY \
    GOSUMDB=$GOSUMDB

# Set working directory
WORKDIR /app

# Copy go module files (go.sum may not exist for some services)
COPY go.* ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o $service main.go

# Production stage
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates tzdata curl && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1001 appgroup && useradd -u 1001 -g appgroup -m -s /usr/sbin/nologin appuser

# Set working directory
WORKDIR /app

# Copy binary from builder stage
COPY --from=builder /app/$service .

# Create necessary directories
RUN mkdir -p /app/tmp && \\
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE $SERVICE_PORT

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:$SERVICE_PORT/health || exit 1

# Run the application
CMD ["./$service"]
EOF
    fi
    
    # Build Docker image
    docker build -t "wealthwatch/$service:latest" .
    
    if [ $? -eq 0 ]; then
        log_info "$service built successfully"
    else
        log_error "Failed to build $service"
        exit 1
    fi
    
    cd - > /dev/null

    if [ "$USE_MINIKUBE_DOCKER" = "0" ] && [ "$LOAD_TO_MINIKUBE" = "1" ]; then
        log_info "Loading image into Minikube: wealthwatch/$service:latest"
        minikube image load "wealthwatch/$service:latest"
    fi
done

log_info "All services built successfully!"

# Show built images
log_info "Built Docker images:"
docker images | grep wealthwatch
