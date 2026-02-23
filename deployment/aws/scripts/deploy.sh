#!/bin/bash

# AWS Production Deployment Script for WealthWatch
# This script automates the deployment process

set -e

# Configuration
AWS_REGION="us-east-1"
ECR_REPOSITORY="wealthwatch"
ECS_CLUSTER="wealthwatch-cluster"
ECS_SERVICE="wealthwatch-service"
CONTAINER_NAME="wealthwatch"

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
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials are not configured. Please run 'aws configure'."
        exit 1
    fi
    
    log_info "Prerequisites check passed."
}

# Build and push Docker image
build_and_push_image() {
    log_info "Building Docker image..."
    
    # Get AWS account ID
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    
    # Login to ECR
    log_info "Logging into ECR..."
    aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}
    
    # Build image
    log_info "Building application image..."
    docker build -t ${ECR_REPOSITORY}:latest .
    
    # Tag image
    log_info "Tagging image for ECR..."
    docker tag ${ECR_REPOSITORY}:latest ${ECR_URI}/${ECR_REPOSITORY}:latest
    
    # Push image
    log_info "Pushing image to ECR..."
    docker push ${ECR_URI}/${ECR_REPOSITORY}:latest
    
    log_info "Docker image built and pushed successfully."
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    log_info "Deploying infrastructure with Terraform..."
    
    cd deployment/aws/terraform
    
    # Initialize Terraform
    log_info "Initializing Terraform..."
    terraform init
    
    # Plan infrastructure
    log_info "Planning infrastructure changes..."
    terraform plan -out=tfplan
    
    # Apply infrastructure
    log_info "Applying infrastructure changes..."
    terraform apply -auto-approve tfplan
    
    cd - > /dev/null
    
    log_info "Infrastructure deployed successfully."
}

# Update ECS service
update_ecs_service() {
    log_info "Updating ECS service..."
    
    # Get current task definition
    TASK_DEFINITION=$(aws ecs describe-services --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE} --query 'services[0].taskDefinition' --output text)
    
    # Create new task definition with updated image
    log_info "Creating new task definition..."
    aws ecs register-task-definition --cli-input-json file://deployment/aws/terraform/task-definition.json
    
    # Update service
    log_info "Updating ECS service..."
    aws ecs update-service --cluster ${ECS_CLUSTER} --service ${ECS_SERVICE} --force-new-deployment
    
    # Wait for service to stabilize
    log_info "Waiting for service to stabilize..."
    aws ecs wait services-stable --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE}
    
    log_info "ECS service updated successfully."
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    # Run migration task
    aws ecs run-task \
        --cluster ${ECS_CLUSTER} \
        --task-definition wealthwatch-migrate \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[subnet-12345,subnet-67890],securityGroups=[sg-12345],assignPublicIp=ENABLED}" \
        --overrides '{"containerOverrides":[{"name":"wealthwatch","command":["./migrate"]}]}'
    
    log_info "Database migrations completed."
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    # Get load balancer DNS
    LOAD_BALANCER_DNS=$(aws elbv2 describe-load-balancers --names wealthwatch-lb --query 'LoadBalancers[0].DNSName' --output text)
    
    # Wait for load balancer to be ready
    log_info "Waiting for load balancer to be ready..."
    sleep 30
    
    # Check health endpoint
    if curl -f "http://${LOAD_BALANCER_DNS}/health" > /dev/null 2>&1; then
        log_info "Health check passed. Application is running successfully."
    else
        log_error "Health check failed. Please check the logs."
        exit 1
    fi
}

# Cleanup
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -f deployment/aws/terraform/tfplan
    log_info "Cleanup completed."
}

# Main deployment function
main() {
    log_info "Starting WealthWatch deployment to AWS..."
    
    check_prerequisites
    build_and_push_image
    deploy_infrastructure
    update_ecs_service
    run_migrations
    health_check
    cleanup
    
    log_info "🎉 Deployment completed successfully!"
    log_info "Application is available at: http://$(aws elbv2 describe-load-balancers --names wealthwatch-lb --query 'LoadBalancers[0].DNSName' --output text)"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "infra")
        check_prerequisites
        deploy_infrastructure
        ;;
    "app")
        check_prerequisites
        build_and_push_image
        update_ecs_service
        health_check
        ;;
    "health")
        health_check
        ;;
    "cleanup")
        cd deployment/aws/terraform
        terraform destroy -auto-approve
        cd - > /dev/null
        log_info "Infrastructure destroyed."
        ;;
    *)
        echo "Usage: $0 {deploy|infra|app|health|cleanup}"
        echo "  deploy  - Full deployment (infrastructure + application)"
        echo "  infra   - Deploy infrastructure only"
        echo "  app     - Deploy application only"
        echo "  health  - Run health check"
        echo "  cleanup - Destroy all infrastructure"
        exit 1
        ;;
esac
