#!/bin/bash

# Minikube setup script for WealthWatch microservices
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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if minikube is installed
    if ! command -v minikube &> /dev/null; then
        log_error "Minikube is not installed. Please install it first:"
        echo "  macOS: brew install minikube"
        echo "  Linux: curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64"
        echo "  Windows: Download from https://minikube.sigs.k8s.io/docs/start/"
        exit 1
    fi
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install it first:"
        echo "  macOS: brew install kubectl"
        echo "  Linux: curl -LO \"https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl\""
        echo "  Windows: Download from https://kubernetes.io/docs/tasks/tools/install-kubectl/"
        exit 1
    fi
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    log_info "Prerequisites check passed."
}

# Start Minikube
start_minikube() {
    log_info "Starting Minikube..."
    
    # Check if minikube is already running
    if minikube status | grep -q "Running"; then
        log_warn "Minikube is already running."
        return
    fi
    
    # Start minikube with sufficient resources.
    # Defaults are intentionally conservative to fit typical Docker Desktop limits.
    MINIKUBE_CPUS=${MINIKUBE_CPUS:-4}
    MINIKUBE_MEMORY=${MINIKUBE_MEMORY:-6000}
    MINIKUBE_DISK_SIZE=${MINIKUBE_DISK_SIZE:-20g}
    MINIKUBE_DRIVER=${MINIKUBE_DRIVER:-docker}
    MINIKUBE_KUBERNETES_VERSION=${MINIKUBE_KUBERNETES_VERSION:-}

    MINIKUBE_START_ARGS=(
        --cpus="$MINIKUBE_CPUS"
        --memory="$MINIKUBE_MEMORY"
        --disk-size="$MINIKUBE_DISK_SIZE"
        --driver="$MINIKUBE_DRIVER"
    )

    if [ -n "$MINIKUBE_KUBERNETES_VERSION" ]; then
        MINIKUBE_START_ARGS+=(--kubernetes-version="$MINIKUBE_KUBERNETES_VERSION")
    fi

    minikube start "${MINIKUBE_START_ARGS[@]}"
    
    # Verify minikube is running
    if minikube status | grep -q "Running"; then
        log_info "Minikube started successfully."
    else
        log_error "Failed to start Minikube."
        exit 1
    fi
}

# Enable addons
enable_addons() {
    log_info "Enabling Minikube addons..."
    
    # Enable required addons
    minikube addons enable ingress
    minikube addons enable metrics-server
    minikube addons enable dashboard
    
    log_info "Addons enabled successfully."
}

# Setup Docker environment
setup_docker_env() {
    log_info "Setting up Docker environment..."
    
    # Set Docker environment variables
    eval $(minikube docker-env)
    
    # Verify Docker can access Minikube
    if docker info &> /dev/null; then
        log_info "Docker environment configured successfully."
    else
        log_error "Failed to configure Docker environment."
        exit 1
    fi
}

# Create namespace
create_namespace() {
    log_info "Creating Kubernetes namespace..."
    
    kubectl create namespace wealthwatch --dry-run=client -o yaml | kubectl apply -f -
    
    log_info "Namespace created successfully."
}

# Show status
show_status() {
    log_info "Minikube Status:"
    echo "================================"
    minikube status
    
    echo ""
    log_info "Cluster Info:"
    echo "================================"
    kubectl cluster-info
    
    echo ""
    log_info "Nodes:"
    echo "================================"
    kubectl get nodes -o wide
    
    echo ""
    log_info "Access Information:"
    echo "================================"
    MINIKUBE_IP=$(minikube ip)
    echo "Minikube IP: $MINIKUBE_IP"
    echo "Kubernetes Dashboard: minikube dashboard"
    echo "Ingress Controller: http://$MINIKUBE_IP"
    
    echo ""
    log_info "Useful Commands:"
    echo "================================"
    echo "  Stop Minikube: minikube stop"
    echo "  Delete Minikube: minikube delete"
    echo "  Access Dashboard: minikube dashboard"
    echo "  SSH into Minikube: minikube ssh"
    echo "  View logs: minikube logs"
    echo "  Get services: kubectl get services -n wealthwatch"
    echo "  Get pods: kubectl get pods -n wealthwatch"
}

# Main function
main() {
    log_info "Setting up Minikube for WealthWatch microservices..."
    
    check_prerequisites
    start_minikube
    enable_addons
    setup_docker_env
    create_namespace
    show_status
    
    log_info "🎉 Minikube setup completed successfully!"
    echo ""
    log_info "Next steps:"
    echo "1. Build services: ./build-services.sh"
    echo "2. Deploy services: ./deploy-services.sh"
    echo "3. Access the application: http://$(minikube ip):8080"
}

# Handle script arguments
case "${1:-setup}" in
    "setup")
        main
        ;;
    "start")
        start_minikube
        ;;
    "stop")
        log_info "Stopping Minikube..."
        minikube stop
        ;;
    "delete")
        log_warn "Deleting Minikube cluster..."
        minikube delete
        ;;
    "status")
        show_status
        ;;
    "dashboard")
        minikube dashboard
        ;;
    *)
        echo "Usage: $0 {setup|start|stop|delete|status|dashboard}"
        echo "  setup     - Complete setup (start + addons + namespace)"
        echo "  start     - Start Minikube only"
        echo "  stop      - Stop Minikube"
        echo "  delete    - Delete Minikube cluster"
        echo "  status    - Show cluster status"
        echo "  dashboard - Open Kubernetes dashboard"
        exit 1
        ;;
esac
