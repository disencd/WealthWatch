# Kubernetes on AWS Deployment Guide

This guide covers deploying the WealthWatch application to AWS using Amazon EKS (Elastic Kubernetes Service) with production-ready configurations.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AWS Load      │    │   Amazon EKS    │    │   Amazon RDS    │
│   Balancer      │────│   Cluster       │────│   PostgreSQL    │
│   (ALB/Ingress) │    │   (Kubernetes)  │    │   (Multi-AZ)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └──────────────│   ElastiCache   │──────────────┘
                        │   (Redis)       │
                        └─────────────────┘
```

## Kubernetes Components

- **EKS Cluster**: Managed Kubernetes service
- **Ingress Controller**: AWS Load Balancer Controller
- **Deployments**: Application pods with auto-scaling
- **Services**: Internal service discovery
- **ConfigMaps/Secrets**: Configuration management
- **Persistent Volumes**: Database storage (via RDS)
- **Horizontal Pod Autoscaler**: Automatic scaling

## Prerequisites

1. AWS CLI installed and configured
2. kubectl installed
3. eksctl installed
4. Helm installed
5. Docker installed
6. Domain name (optional, for HTTPS)

## Quick Start

### 1. Create EKS Cluster

```bash
# Create cluster with eksctl
eksctl create cluster \
  --name wealthwatch-cluster \
  --region us-east-1 \
  --version 1.28 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 10 \
  --managed
```

### 2. Install AWS Load Balancer Controller

```bash
# Add Helm repository
helm repo add eks https://aws.github.io/eks-charts
helm repo update

# Install the controller
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=wealthwatch-cluster \
  --set serviceAccount.create=true \
  --set serviceAccount.name=aws-load-balancer-controller
```

### 3. Deploy Application

```bash
# Apply all Kubernetes manifests
kubectl apply -f k8s/
```

---

## Detailed Deployment Steps

### Step 1: Infrastructure Setup

#### VPC and Networking
The EKS cluster creates a dedicated VPC with:
- Public and private subnets
- Internet gateway and NAT gateways
- Route tables for proper routing

#### Security Groups
- Control plane security group
- Node security group
- Application security groups

### Step 2: EKS Cluster Configuration

#### Cluster Creation
```bash
eksctl create cluster \
  --name wealthwatch-cluster \
  --region us-east-1 \
  --version 1.28 \
  --with-oidc \
  --managed
```

#### Node Groups
```bash
# Create node group for application pods
eksctl create nodegroup \
  --cluster wealthwatch-cluster \
  --region us-east-1 \
  --name app-nodes \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 10 \
  --node-labels purpose=app
```

### Step 3: Storage and Database

#### RDS PostgreSQL
```bash
# Create RDS subnet group
aws rds create-db-subnet-group \
  --db-subnet-group-name wealthwatch-db-subnet-group \
  --subnet-ids subnet-12345 subnet-67890 \
  --db-subnet-group-description "Subnet group for WealthWatch RDS"

# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier wealthwatch-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.4 \
  --master-username wealthwatch \
  --master-user-password your-secure-password \
  --allocated-storage 100 \
  --vpc-security-group-ids sg-12345 \
  --db-subnet-group-name wealthwatch-db-subnet-group \
  --backup-retention-period 30 \
  --multi-az \
  --storage-encrypted
```

#### ElastiCache Redis
```bash
# Create Redis subnet group
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name wealthwatch-redis-subnet-group \
  --cache-subnet-group-description "Subnet group for WealthWatch Redis" \
  --subnet-ids subnet-12345 subnet-67890

# Create Redis cluster
aws elasticache create-replication-group \
  --replication-group-id wealthwatch-redis \
  --replication-group-description "WealthWatch Redis cluster" \
  --num-cache-clusters 2 \
  --engine redis \
  --cache-node-type cache.t3.micro \
  --security-group-ids sg-12345 \
  --cache-subnet-group-name wealthwatch-redis-subnet-group \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled \
  --auth-token your-redis-token
```

### Step 4: Kubernetes Manifests

#### Namespace
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: wealthwatch
```

#### ConfigMaps
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: wealthwatch-config
  namespace: wealthwatch
data:
  GIN_MODE: "release"
  PORT: "8080"
  DB_HOST: "wealthwatch-db.xxxx.us-east-1.rds.amazonaws.com"
  DB_PORT: "5432"
  DB_NAME: "wealthwatch_prod"
  DB_USER: "wealthwatch"
  DB_SSLMODE: "require"
  REDIS_HOST: "wealthwatch-redis.xxxxx.clustercfg.use1.cache.amazonaws.com"
  REDIS_PORT: "6379"
```

#### Secrets
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: wealthwatch-secrets
  namespace: wealthwatch
type: Opaque
data:
  DB_PASSWORD: <base64-encoded-password>
  JWT_SECRET: <base64-encoded-jwt-secret>
  REDIS_AUTH_TOKEN: <base64-encoded-redis-token>
```

#### Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wealthwatch
  namespace: wealthwatch
spec:
  replicas: 3
  selector:
    matchLabels:
      app: wealthwatch
  template:
    metadata:
      labels:
        app: wealthwatch
    spec:
      containers:
      - name: wealthwatch
        image: your-ecr-repo/wealthwatch:latest
        ports:
        - containerPort: 8080
        envFrom:
        - configMapRef:
            name: wealthwatch-config
        - secretRef:
            name: wealthwatch-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: wealthwatch-service
  namespace: wealthwatch
spec:
  selector:
    app: wealthwatch
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: ClusterIP
```

#### Ingress
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: wealthwatch-ingress
  namespace: wealthwatch
  annotations:
    kubernetes.io/ingress.class: "alb"
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS-1-2-2017-01
spec:
  tls:
  - hosts:
    - wealthwatch.yourdomain.com
    secretName: wealthwatch-tls
  rules:
  - host: wealthwatch.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: wealthwatch-service
            port:
              number: 80
```

#### Horizontal Pod Autoscaler
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: wealthwatch-hpa
  namespace: wealthwatch
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: wealthwatch
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Step 5: Deployment Commands

```bash
# Create namespace
kubectl create namespace wealthwatch

# Apply ConfigMaps and Secrets
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# Deploy application
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# Set up auto-scaling
kubectl apply -f k8s/hpa.yaml

# Check deployment status
kubectl get pods -n wealthwatch
kubectl get services -n wealthwatch
kubectl get ingress -n wealthwatch
```

---

## Monitoring and Observability

### Prometheus and Grafana
```bash
# Install Prometheus Operator
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring \
  --create-namespace

# Install Grafana dashboards
kubectl apply -f k8s/monitoring/grafana-dashboards.yaml
```

### Fluentd for Logging
```bash
# Install Fluentd
helm repo add fluent https://fluent.github.io/helm-charts
helm install fluent fluent/fluentd \
  -n logging \
  --create-namespace
```

---

## CI/CD Pipeline

### GitHub Actions for Kubernetes
```yaml
name: Deploy to EKS

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Update kubeconfig
        run: aws eks update-kubeconfig --name wealthwatch-cluster --region us-east-1
      
      - name: Build and push Docker image
        run: |
          # Build and push to ECR
          aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_REGISTRY
          docker build -t $ECR_REGISTRY/wealthwatch:$GITHUB_SHA .
          docker push $ECR_REGISTRY/wealthwatch:$GITHUB_SHA
      
      - name: Deploy to Kubernetes
        run: |
          # Update image in deployment
          kubectl set image deployment/wealthwatch wealthwatch=$ECR_REGISTRY/wealthwatch:$GITHUB_SHA -n wealthwatch
          kubectl rollout status deployment/wealthwatch -n wealthwatch
```

---

## Security Best Practices

### 1. Network Policies
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: wealthwatch-netpol
  namespace: wealthwatch
spec:
  podSelector:
    matchLabels:
      app: wealthwatch
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
```

### 2. Pod Security Policies
```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: wealthwatch-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

### 3. RBAC
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: wealthwatch-sa
  namespace: wealthwatch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: wealthwatch-role
  namespace: wealthwatch
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: wealthwatch-rolebinding
  namespace: wealthwatch
subjects:
- kind: ServiceAccount
  name: wealthwatch-sa
  namespace: wealthwatch
roleRef:
  kind: Role
  name: wealthwatch-role
  apiGroup: rbac.authorization.k8s.io
```

---

## Backup and Disaster Recovery

### 1. Database Backups
- Enable automated backups in RDS
- Set retention period to 30 days
- Enable point-in-time recovery
- Regular backup testing

### 2. etcd Backups
```bash
# Create etcd backup
eksctl utils install-csi-driver --name wealthwatch-cluster --region us-east-1
```

### 3. Application State Backup
- Use Velero for Kubernetes backups
- Backup PVCs, configurations, and secrets
- Cross-region backup replication

---

## Cost Optimization

### 1. Right-sizing Resources
- Monitor resource utilization
- Adjust pod requests and limits
- Use appropriate instance types

### 2. Cluster Autoscaler
```bash
# Install cluster autoscaler
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  -n kube-system \
  --set autoDiscovery.clusterName=wealthwatch-cluster \
  --set awsRegion=us-east-1
```

### 3. Spot Instances
```bash
# Create node group with spot instances
eksctl create nodegroup \
  --cluster wealthwatch-cluster \
  --region us-east-1 \
  --name spot-nodes \
  --node-type t3.medium \
  --nodes 1 \
  --nodes-min 0 \
  --nodes-max 5 \
  --spot \
  --instance-types t3.medium,t3.large,t3.xlarge
```

---

## Troubleshooting

### Common Issues

1. **Pod Not Starting**
   ```bash
   kubectl describe pod <pod-name> -n wealthwatch
   kubectl logs <pod-name> -n wealthwatch
   ```

2. **Service Not Accessible**
   ```bash
   kubectl get svc -n wealthwatch
   kubectl describe svc wealthwatch-service -n wealthwatch
   ```

3. **Ingress Not Working**
   ```bash
   kubectl get ingress -n wealthwatch
   kubectl describe ingress wealthwatch-ingress -n wealthwatch
   ```

4. **HPA Not Scaling**
   ```bash
   kubectl get hpa -n wealthwatch
   kubectl describe hpa wealthwatch-hpa -n wealthwatch
   ```

### Monitoring Commands
```bash
# Check cluster status
kubectl get nodes
kubectl get pods -A

# Check resource usage
kubectl top nodes
kubectl top pods -n wealthwatch

# Check events
kubectl get events -n wealthwatch --sort-by=.metadata.creationTimestamp
```

---

## Scaling Strategy

### 1. Horizontal Scaling
- Use HPA for pod auto-scaling
- Use Cluster Autoscaler for node scaling
- Implement custom metrics for application-specific scaling

### 2. Vertical Scaling
- Monitor resource utilization
- Adjust pod resource requests and limits
- Use Vertical Pod Autoscaler (VPA)

### 3. Multi-Region Deployment
- Deploy across multiple AWS regions
- Use Route 53 for DNS failover
- Implement cross-region data replication

This Kubernetes approach provides excellent scalability, resilience, and operational efficiency for your WealthWatch application on AWS.
