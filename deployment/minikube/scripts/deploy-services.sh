#!/bin/bash

# Deploy script for all microservices to Minikube
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

# Check if Minikube is running
if ! minikube status | grep -q "Running"; then
    log_error "Minikube is not running. Please start Minikube first."
    exit 1
fi

# Refresh kubeconfig/context in case Minikube API endpoint changed
minikube update-context

# Set current context to minikube
kubectl config use-context minikube

# Apply namespace
log_info "Creating namespace..."
kubectl apply --validate=false -f k8s/namespace.yaml

# Apply database
log_info "Deploying PostgreSQL..."
kubectl apply --validate=false -f k8s/postgres.yaml

# Apply Redis
log_info "Deploying Redis..."
kubectl apply --validate=false -f k8s/redis.yaml

# Wait for database to be ready
log_info "Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready --timeout=300s pod -l app=postgres -n wealthwatch

# Wait for Redis to be ready
log_info "Waiting for Redis to be ready..."
kubectl wait --for=condition=ready --timeout=300s pod -l app=redis -n wealthwatch

# Apply services
services=(
    "auth-service"
    "expense-service"
    "balance-service"
)

for service in "${services[@]}"; do
    log_info "Deploying $service..."
    kubectl apply --validate=false -f "k8s/$service.yaml"
    
    # Wait for service to be ready
    kubectl wait --for=condition=available --timeout=300s deployment/$service -n wealthwatch
done

# Apply API Gateway
log_info "Deploying API Gateway..."
kubectl apply --validate=false -f k8s/api-gateway.yaml

# Wait for API Gateway to be ready
kubectl wait --for=condition=available --timeout=300s deployment/api-gateway -n wealthwatch

# Show deployment status
log_info "Deployment completed successfully!"
echo ""
log_info "Pods in wealthwatch namespace:"
kubectl get pods -n wealthwatch

echo ""
log_info "Services in wealthwatch namespace:"
kubectl get services -n wealthwatch

echo ""
log_info "Access Information:"
echo "================================"

# Get API Gateway URL
if command -v minikube &> /dev/null; then
    MINIKUBE_IP=$(minikube ip)
    API_GATEWAY_PORT=$(kubectl get service api-gateway -n wealthwatch -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "8080")
    
    echo "API Gateway: http://$MINIKUBE_IP:$API_GATEWAY_PORT"
    echo ""
    echo "Service Endpoints (internal):"
    echo "  Auth Service: http://auth-service:8001"
    echo "  Expense Service: http://expense-service:8003"
    echo "  Balance Service: http://balance-service:8004"
    echo ""
    echo "Database Access:"
    echo "  PostgreSQL: postgres-service:5432"
    echo "  Redis: redis-service:6379"
    echo ""
    echo "Useful Commands:"
    echo "  kubectl logs -f deployment/auth-service -n wealthwatch"
    echo "  kubectl port-forward service/api-gateway 8080:8080 -n wealthwatch"
    echo "  minikube dashboard"
else
    echo "Minikube not found. Please check service URLs manually."
fi

# Test connectivity
log_info "Testing service connectivity..."
sleep 10

# Test API Gateway health
if curl -f "http://$MINIKUBE_IP:$API_GATEWAY_PORT/health" &> /dev/null; then
    log_info "API Gateway is healthy"
else
    log_warn "API Gateway health check failed"
fi

# Test individual services
for service in "${services[@]}"; do
    service_name=$(echo $service | sed 's/-service//')
    if kubectl exec -n wealthwatch deployment/$service -- curl -f "http://localhost:8001/health" &> /dev/null; then
        log_info "$service_name is healthy"
    else
        log_warn "$service_name health check failed"
    fi
done

log_info "Deployment and health checks completed!"
