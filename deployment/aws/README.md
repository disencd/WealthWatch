# AWS Production Deployment Guide

This guide covers deploying the WealthWatch application to AWS using modern, production-ready infrastructure.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │────│   ECS Cluster   │────│   RDS PostgreSQL│
│   (ALB)         │    │   (Fargate)     │    │   (Multi-AZ)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └──────────────│   ElastiCache   │──────────────┘
                        │   (Redis)       │
                        └─────────────────┘
```

## Prerequisites

1. AWS CLI installed and configured
2. Docker installed
3. Terraform installed (optional but recommended)
4. Domain name (optional, for HTTPS)

## Deployment Options

### Option 1: AWS ECS with Fargate (Recommended)
- Serverless containers
- Auto-scaling
- Load balancing
- High availability

### Option 2: AWS EC2 with Docker
- Full control over instances
- Cost-effective for small scale
- Manual scaling

### Option 3: AWS App Runner
- Simple deployment
- Automatic scaling
- Limited configuration

---

## Option 1: ECS with Fargate (Production Ready)

### 1. Create ECR Repository

```bash
# Create repository
aws ecr create-repository \
    --repository-name wealthwatch \
    --region us-east-1

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
```

### 2. Build and Push Docker Image

```bash
# Build image
docker build -t wealthwatch .

# Tag for ECR
docker tag wealthwatch:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/wealthwatch:latest

# Push to ECR
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/wealthwatch:latest
```

### 3. Create Infrastructure with Terraform

See `terraform/` directory for complete infrastructure setup.

### 4. Deploy with ECS

```bash
# Create task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create service
aws ecs create-service --cluster wealthwatch-cluster --service-name wealthwatch-service --task-definition wealthwatch:1 --desired-count 2 --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[subnet-12345,subnet-67890],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
```

---

## Option 2: EC2 with Docker Compose

### 1. Launch EC2 Instance

```bash
# Create EC2 instance with Amazon Linux 2
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --instance-type t3.medium \
    --key-name your-key-pair \
    --security-group-ids sg-12345 \
    --subnet-id subnet-12345 \
    --user-data file://user-data.sh
```

### 2. User Data Script (user-data.sh)

```bash
#!/bin/bash
yum update -y
yum install -y docker git
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install docker-compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Clone and deploy
cd /opt
git clone <your-repo>
cd wealthwatch
docker-compose up -d
```

---

## Environment Configuration

### Production Environment Variables

Create `.env.production`:

```env
# Database (RDS)
DB_HOST=your-rds-endpoint.rds.amazonaws.com
DB_PORT=5432
DB_USER=wealthwatch_prod
DB_PASSWORD=your-secure-password
DB_NAME=wealthwatch_prod
DB_SSLMODE=require

# Redis (ElastiCache)
REDIS_HOST=your-redis-cluster.xxxxxx.0001.use1.cache.amazonaws.com
REDIS_PORT=6379

# JWT
JWT_SECRET=your-super-secure-jwt-secret-key-min-32-chars
JWT_EXPIRES_IN=24h

# Server
GIN_MODE=release
PORT=8080
LOG_LEVEL=info

# Email (SES)
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_EMAIL=your-email@yourdomain.com
SMTP_PASSWORD=your-smtp-password

# Monitoring
SENTRY_DSN=your-sentry-dsn
NEW_RELIC_LICENSE_KEY=your-newrelic-key
```

---

## Security Best Practices

### 1. VPC and Networking
- Use private subnets for RDS and ElastiCache
- Use public subnets for load balancer
- Implement proper security groups
- Use VPC endpoints for AWS services

### 2. Secrets Management
- Use AWS Secrets Manager for database credentials
- Use Parameter Store for configuration
- Rotate secrets regularly

### 3. SSL/TLS
- Use AWS Certificate Manager for SSL certificates
- Enforce HTTPS only
- Use security headers

### 4. Access Control
- Use IAM roles for EC2/ECS tasks
- Implement least privilege access
- Use MFA for all IAM users

---

## Monitoring and Logging

### 1. CloudWatch Integration
- Application logs to CloudWatch Logs
- Metrics to CloudWatch Metrics
- Set up alarms for critical metrics

### 2. Application Performance
- Use AWS X-Ray for tracing
- Implement health checks
- Monitor response times

### 3. Error Tracking
- Integrate Sentry for error tracking
- Set up alerts for high error rates

---

## Backup and Disaster Recovery

### 1. Database Backups
- Enable automated backups for RDS
- Set retention period (30 days)
- Enable point-in-time recovery
- Regular backup testing

### 2. Multi-AZ Deployment
- Deploy across multiple Availability Zones
- Configure failover
- Test disaster recovery procedures

---

## Scaling Strategy

### 1. Auto Scaling
- Set up ECS auto scaling based on CPU/memory
- Configure target tracking policies
- Set minimum and maximum capacity

### 2. Database Scaling
- Start with db.t3.medium
- Monitor performance metrics
- Scale up when needed
- Consider read replicas for read-heavy workloads

---

## CI/CD Pipeline

### GitHub Actions Example

```yaml
name: Deploy to AWS
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
      
      - name: Build, tag, and push image to Amazon ECR
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: wealthwatch
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
      
      - name: Update ECS service
        run: |
          aws ecs update-service --cluster wealthwatch-cluster --service wealthwatch-service --force-new-deployment
```

---

## Cost Optimization

### 1. Instance Sizing
- Start with appropriate instance sizes
- Monitor utilization
- Right-size based on actual usage

### 2. Reserved Instances
- Consider reserved instances for steady workloads
- Use savings plans for flexible pricing

### 3. Storage Optimization
- Use appropriate storage types
- Implement lifecycle policies
- Clean up unused resources

---

## Deployment Checklist

- [ ] Set up VPC and networking
- [ ] Create RDS PostgreSQL instance
- [ ] Set up ElastiCache Redis cluster
- [ ] Configure security groups
- [ ] Create ECS cluster and service
- [ ] Set up Application Load Balancer
- [ ] Configure SSL certificate
- [ ] Set up monitoring and logging
- [ ] Configure backup and disaster recovery
- [ ] Implement CI/CD pipeline
- [ ] Test failover procedures
- [ ] Performance testing
- [ ] Security audit

---

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Check security group rules
   - Verify VPC routing
   - Check credentials in Secrets Manager

2. **Container Failures**
   - Check CloudWatch logs
   - Verify task definition
   - Check resource limits

3. **Load Balancer Issues**
   - Check target group health
   - Verify security groups
   - Check listener rules

### Monitoring Commands

```bash
# Check ECS service status
aws ecs describe-services --cluster wealthwatch-cluster --services wealthwatch-service

# Check running tasks
aws ecs list-tasks --cluster wealthwatch-cluster

# Check CloudWatch logs
aws logs tail /ecs/wealthwatch --follow

# Check RDS status
aws rds describe-db-instances --db-instance-identifier wealthwatch-db
```
