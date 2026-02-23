#!/bin/bash

# Kubernetes on AWS Setup Script for Splitwise
# This script sets up EKS cluster and required components

set -e

# Configuration
CLUSTER_NAME="splitwise-cluster"
REGION="us-east-1"
NODE_GROUP_NAME="splitwise-nodes"
NODE_TYPE="t3.medium"
MIN_NODES=2
MAX_NODES=10
DESIRED_NODES=3
KUBERNETES_VERSION="1.28"

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
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install it first."
        exit 1
    fi
    
    # Check eksctl
    if ! command -v eksctl &> /dev/null; then
        log_error "eksctl is not installed. Please install it first."
        exit 1
    fi
    
    # Check Helm
    if ! command -v helm &> /dev/null; then
        log_error "Helm is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials are not configured. Please run 'aws configure'."
        exit 1
    fi
    
    log_info "Prerequisites check passed."
}

# Create EKS cluster
create_cluster() {
    log_info "Creating EKS cluster: ${CLUSTER_NAME}"
    
    # Create cluster config
    cat > cluster-config.yaml <<EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: ${CLUSTER_NAME}
  region: ${REGION}
  version: "${KUBERNETES_VERSION}"

iam:
  withOIDC: true

managedNodeGroups:
  - name: ${NODE_GROUP_NAME}
    instanceType: ${NODE_TYPE}
    minSize: ${MIN_NODES}
    maxSize: ${MAX_NODES}
    desiredCapacity: ${DESIRED_NODES}
    volumeSize: 50
    ssh:
      allow: true
    iam:
      withAddonPolicies:
        autoScaler: true
        cloudWatch: true
        ebs: true
        efs: true
        albIngress: true
    labels:
      purpose: app
    taints: []
    tags:
      Environment: production
      Application: splitwise

addons:
  - name: vpc-cni
  - name: coredns
  - name: kube-proxy
  - name: aws-ebs-csi-driver

cloudWatch:
  clusterLogging:
    enable: ["api", "audit", "authenticator", "controllerManager", "scheduler"]
EOF

    # Create cluster
    eksctl create cluster -f cluster-config.yaml
    
    log_info "EKS cluster created successfully."
}

# Install AWS Load Balancer Controller
install_alb_controller() {
    log_info "Installing AWS Load Balancer Controller..."
    
    # Create service account
    kubectl apply -f - <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  labels:
    app.kubernetes.io/name: aws-load-balancer-controller
  name: aws-load-balancer-controller
  namespace: kube-system
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/AWSLoadBalancerControllerRole
EOF

    # Add Helm repository
    helm repo add eks https://aws.github.io/eks-charts
    helm repo update

    # Install the controller
    helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
        -n kube-system \
        --set clusterName=${CLUSTER_NAME} \
        --set serviceAccount.create=false \
        --set serviceAccount.name=aws-load-balancer-controller
    
    log_info "AWS Load Balancer Controller installed."
}

# Install Cluster Autoscaler
install_cluster_autoscaler() {
    log_info "Installing Cluster Autoscaler..."
    
    helm repo add autoscaler https://kubernetes.github.io/autoscaler
    helm repo update

    helm install cluster-autoscaler autoscaler/cluster-autoscaler \
        -n kube-system \
        --set autoDiscovery.clusterName=${CLUSTER_NAME} \
        --set awsRegion=${REGION} \
        --set rbac.create=true \
        --set rbac.serviceAccount.create=true \
        --set rbac.serviceAccount.name=cluster-autoscaler \
        --set extraArgs.balance-similar-node-groups=true \
        --set extraArgs.skip-nodes-with-local-storage=false \
        --set extraArgs.skip-nodes-with-system-pods=false \
        --set extraArgs.max-node-provision-time=15m
    
    log_info "Cluster Autoscaler installed."
}

# Install Metrics Server
install_metrics_server() {
    log_info "Installing Metrics Server..."
    
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    
    # Wait for metrics server to be ready
    kubectl wait --for=condition=available --timeout=300s deployment/metrics-server -n kube-system
    
    log_info "Metrics Server installed."
}

# Install Prometheus and Grafana (optional)
install_monitoring() {
    log_info "Installing Prometheus and Grafana..."
    
    # Create monitoring namespace
    kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
    
    # Add Prometheus Helm repository
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update

    # Install Prometheus stack
    helm install prometheus prometheus-community/kube-prometheus-stack \
        -n monitoring \
        --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
        --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=gp3 \
        --set grafana.adminPassword=admin123 \
        --set grafana.service.type=LoadBalancer \
        --set grafana.ingress.enabled=true \
        --set grafana.ingress.hosts=grafana.splitwise.local
    
    log_info "Prometheus and Grafana installed."
}

# Create IAM role for service account
create_irsa() {
    log_info "Creating IAM role for service account..."
    
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    OIDC_PROVIDER=$(aws eks describe-cluster --name ${CLUSTER_NAME} --region ${REGION} --query "cluster.identity.oidc.issuer" --output text | sed -e "s/^https:\/\///")
    
    # Create trust policy
    cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_PROVIDER}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OIDC_PROVIDER}:sub": "system:serviceaccount:splitwise:splitwise-sa"
        }
      }
    }
  ]
}
EOF

    # Create IAM role
    aws iam create-role --role-name splitwise-eks-role --assume-role-policy-document file://trust-policy.json || true
    
    # Attach policies
    aws iam attach-role-policy --role-name splitwise-eks-role --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
    aws iam attach-role-policy --role-name splitwise-eks-role --policy-arn arn:aws:iam::aws:policy/CloudWatchFullAccess
    
    log_info "IAM role for service account created."
}

# Setup ECR registry secret
setup_ecr_secret() {
    log_info "Setting up ECR registry secret..."
    
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    REGION=${REGION}
    ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
    
    # Create namespace if it doesn't exist
    kubectl create namespace splitwise --dry-run=client -o yaml | kubectl apply -f -
    
    # Create secret
    kubectl create secret generic ecr-registry-secret \
        --from-file=.dockerconfigjson=/dev/stdin \
        --type=kubernetes.io/dockerconfigjson \
        -n splitwise \
        <<<$(aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY} && cat ~/.docker/config.json | base64 -w 0)
    
    log_info "ECR registry secret created."
}

# Deploy application manifests
deploy_app() {
    log_info "Deploying application manifests..."
    
    # Apply all manifests
    kubectl apply -f k8s/namespace.yaml
    kubectl apply -f k8s/rbac.yaml
    kubectl apply -f k8s/storage.yaml
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/secret.yaml
    kubectl apply -f k8s/deployment.yaml
    kubectl apply -f k8s/service.yaml
    kubectl apply -f k8s/ingress.yaml
    kubectl apply -f k8s/hpa.yaml
    kubectl apply -f k8s/networkpolicy.yaml
    
    log_info "Application manifests deployed."
}

# Wait for deployment to be ready
wait_for_deployment() {
    log_info "Waiting for deployment to be ready..."
    
    # Wait for pods to be ready
    kubectl wait --for=condition=available --timeout=600s deployment/splitwise -n splitwise
    
    # Wait for ingress to be ready
    kubectl wait --for=condition=ready --timeout=600s ingress/splitwise-ingress -n splitwise
    
    log_info "Deployment is ready."
}

# Show cluster information
show_info() {
    log_info "Cluster Information:"
    echo "================================"
    echo "Cluster Name: ${CLUSTER_NAME}"
    echo "Region: ${REGION}"
    echo "Kubernetes Version: ${KUBERNETES_VERSION}"
    echo ""
    
    log_info "Access Information:"
    echo "================================"
    
    # Get load balancer URL
    INGRESS_URL=$(kubectl get ingress splitwise-ingress -n splitwise -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    echo "Application URL: http://${INGRESS_URL}"
    
    # Get Grafana URL (if monitoring is installed)
    if kubectl get service prometheus-grafana -n monitoring &> /dev/null; then
        GRAFANA_URL=$(kubectl get service prometheus-grafana -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
        echo "Grafana URL: http://${GRAFANA_URL}"
        echo "Grafana Username: admin"
        echo "Grafana Password: admin123"
    fi
    
    echo ""
    log_info "Useful Commands:"
    echo "================================"
    echo "Update kubeconfig: aws eks update-kubeconfig --name ${CLUSTER_NAME} --region ${REGION}"
    echo "Check pods: kubectl get pods -n splitwise"
    echo "Check services: kubectl get services -n splitwise"
    echo "Check ingress: kubectl get ingress -n splitwise"
    echo "Check HPA: kubectl get hpa -n splitwise"
    echo "Check logs: kubectl logs -f deployment/splitwise -n splitwise"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -f cluster-config.yaml trust-policy.json
    log_info "Cleanup completed."
}

# Main function
main() {
    log_info "Starting Kubernetes on AWS setup for Splitwise..."
    
    check_prerequisites
    create_cluster
    create_irsa
    install_alb_controller
    install_cluster_autoscaler
    install_metrics_server
    setup_ecr_secret
    
    # Optional: Install monitoring
    read -p "Do you want to install Prometheus and Grafana? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_monitoring
    fi
    
    deploy_app
    wait_for_deployment
    show_info
    cleanup
    
    log_info "🎉 Kubernetes setup completed successfully!"
}

# Handle script arguments
case "${1:-setup}" in
    "setup")
        main
        ;;
    "cluster")
        check_prerequisites
        create_cluster
        ;;
    "addons")
        install_alb_controller
        install_cluster_autoscaler
        install_metrics_server
        ;;
    "monitoring")
        install_monitoring
        ;;
    "deploy")
        deploy_app
        wait_for_deployment
        ;;
    "cleanup")
        eksctl delete cluster --name ${CLUSTER_NAME} --region ${REGION}
        ;;
    *)
        echo "Usage: $0 {setup|cluster|addons|monitoring|deploy|cleanup}"
        echo "  setup     - Complete setup (cluster + addons + app)"
        echo "  cluster   - Create EKS cluster only"
        echo "  addons    - Install addons only"
        echo "  monitoring- Install monitoring only"
        echo "  deploy    - Deploy application only"
        echo "  cleanup   - Delete cluster"
        exit 1
        ;;
esac
