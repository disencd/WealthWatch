# Local Minikube Deployment - Microservices Architecture

This guide covers deploying the WealthWatch application as microservices locally using Minikube.

## Microservices Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │────│   Auth Service  │    │   User Service  │
│   (Kong/Nginx)  │    │   (Go)          │    │   (Go)          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         │              │   Expense       │              │
         └──────────────│   Service       │──────────────┘
                        │   (Go)          │
                        └─────────────────┘
                                 │
         ┌─────────────────┐    │    ┌─────────────────┐
         │   Balance       │────┼────│   Settlement     │
         │   Service       │    │    │   Service       │
         │   (Go)          │    │    │   (Go)          │
         └─────────────────┘    │    └─────────────────┘
                                │
         ┌─────────────────┐    │    ┌─────────────────┐
         │   Notification  │────┼────│   PostgreSQL    │
         │   Service       │    │    │   (StatefulSet) │
         │   (Go)          │    │    └─────────────────┘
         └─────────────────┘    │
                                │
         ┌─────────────────┐    │
         │   Redis         │────┘
         │   (Cache)       │
         └─────────────────┘
```

## Services Overview

### 1. API Gateway
- **Port**: 8080
- **Purpose**: Route requests to appropriate microservices
- **Technology**: Kong or Nginx

### 2. Auth Service
- **Port**: 8001
- **Purpose**: User authentication and authorization
- **Database**: PostgreSQL (users table)

### 3. User Service
- **Port**: 8002
- **Purpose**: User profile management
- **Database**: PostgreSQL (users, profiles tables)

### 4. Expense Service
- **Port**: 8003
- **Purpose**: Expense creation and management
- **Database**: PostgreSQL (expenses, splits tables)

### 5. Balance Service
- **Port**: 8004
- **Purpose**: Balance calculations and tracking
- **Database**: PostgreSQL (balances table)

### 6. Settlement Service
- **Port**: 8005
- **Purpose**: Payment settlements
- **Database**: PostgreSQL (settlements table)

### 7. Notification Service
- **Port**: 8006
- **Purpose**: Email and push notifications
- **Queue**: Redis (for async processing)

## Prerequisites

1. **Minikube** installed
2. **kubectl** installed
3. **Docker** installed
4. **Helm** installed (optional)

## Quick Start

### 1. Start Minikube
```bash
# Start Minikube with sufficient resources
minikube start --cpus=4 --memory=8192 --disk-size=20g

# Enable addons
minikube addons enable ingress
minikube addons enable metrics-server
```

### 2. Build and Deploy Services
```bash
# Navigate to deployment directory
cd deployment/minikube

# Build all services
./build-services.sh

# Deploy all services
./deploy-services.sh
```

### 3. Access the Application
```bash
# Get the Minikube IP
minikube ip

# Access the application
# API Gateway: http://$(minikube ip):8080
# Auth Service: http://$(minikube ip):8001
# etc.
```

## Service Communication

### Internal Communication
- Services communicate via HTTP on internal cluster IPs
- Service discovery via Kubernetes DNS
- Example: `http://auth-service:8001/api/v1/auth/login`

### External Communication
- All external traffic goes through API Gateway
- API Gateway handles authentication, rate limiting, and routing

### Database Access
- Each service has its own database schema
- Shared database instance with logical separation
- Connection pooling and retry logic implemented

## Development Workflow

### 1. Local Development
```bash
# Run individual service locally
cd services/auth
go run main.go

# Run with local database
docker-compose -f docker-compose.dev.yml up
```

### 2. Testing
```bash
# Run tests for all services
./test-services.sh

# Run integration tests
./integration-tests.sh
```

### 3. Monitoring
```bash
# Check service status
kubectl get pods -n wealthwatch

# View logs
kubectl logs -f deployment/auth-service -n wealthwatch

# Access service dashboards
minikube dashboard
```

## Configuration

### Environment Variables
Each service uses environment variables for configuration:
- Database connection strings
- Redis connection
- Service ports
- JWT secrets
- External API keys

### Service Discovery
Services discover each other using Kubernetes DNS:
- `auth-service.wealthwatch.svc.cluster.local:8001`
- `user-service.wealthwatch.svc.cluster.local:8002`
- etc.

## Data Management

### Database Schema
Each service owns its database schema:
- **Auth Service**: users, sessions
- **User Service**: user_profiles, preferences
- **Expense Service**: expenses, splits, categories
- **Balance Service**: balances, transactions
- **Settlement Service**: settlements, payments
- **Notification Service**: notifications, templates

### Database Migrations
Each service manages its own migrations:
```bash
# Run migrations for auth service
kubectl exec deployment/auth-service -n wealthwatch -- ./migrate up
```

## Scaling

### Horizontal Scaling
```bash
# Scale individual services
kubectl scale deployment auth-service --replicas=3 -n wealthwatch
kubectl scale deployment expense-service --replicas=5 -n wealthwatch
```

### Auto-scaling
```bash
# Enable HPA for services
kubectl apply -f monitoring/hpa/
```

## Troubleshooting

### Common Issues

1. **Service Not Starting**
   ```bash
   # Check pod logs
   kubectl logs -f deployment/auth-service -n wealthwatch
   
   # Check events
   kubectl get events -n wealthwatch --sort-by=.metadata.creationTimestamp
   ```

2. **Database Connection Issues**
   ```bash
   # Check database connectivity
   kubectl exec deployment/auth-service -n wealthwatch -- ping postgres-service
   ```

3. **Service Communication Issues**
   ```bash
   # Test service connectivity
   kubectl exec deployment/auth-service -n wealthwatch -- curl http://user-service:8002/health
   ```

### Debugging Tools
```bash
# Port forward to local machine
kubectl port-forward service/auth-service 8001:8001 -n wealthwatch

# Exec into pod
kubectl exec -it deployment/auth-service -n wealthwatch -- sh

# Network debugging
kubectl run debug-pod --image=nicolaka/netshoot -it --rm -- /bin/bash
```

## Performance Tuning

### Resource Limits
Each service is configured with appropriate resource limits:
- CPU: 100-500m
- Memory: 128-512Mi
- Based on service requirements

### Database Optimization
- Connection pooling
- Query optimization
- Indexing strategy
- Read replicas for read-heavy services

### Caching Strategy
- Redis for session storage
- Application-level caching
- CDN for static assets

## Security

### Service-to-Service Authentication
- JWT tokens for internal communication
- mTLS for sensitive services
- API keys for external services

### Network Policies
- Restrict traffic between services
- Only allow necessary ports
- Default deny all policy

### Secrets Management
- Kubernetes Secrets for sensitive data
- Environment-specific configurations
- Regular secret rotation

This microservices architecture provides better scalability, maintainability, and isolation compared to a monolithic approach, while still being easy to develop and test locally.
