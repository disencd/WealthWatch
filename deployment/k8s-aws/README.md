# Kubernetes on AWS Deployment Guide

This guide covers deploying the Splitwise application to AWS using Amazon EKS (Elastic Kubernetes Service) with production-ready configurations.

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
  --name splitwise-cluster \
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
  --set clusterName=splitwise-cluster \
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
  --name splitwise-cluster \
  --region us-east-1 \
  --version 1.28 \
  --with-oidc \
  --managed
```

#### Node Groups
```bash
# Create node group for application pods
eksctl create nodegroup \
  --cluster splitwise-cluster \
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
  --db-subnet-group-name splitwise-db-subnet-group \
  --subnet-ids subnet-12345 subnet-67890 \
  --db-subnet-group-description "Subnet group for Splitwise RDS"

# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier splitwise-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.4 \
  --master-username splitwise \
  --master-user-password your-secure-password \
  --allocated-storage 100 \
  --vpc-security-group-ids sg-12345 \
  --db-subnet-group-name splitwise-db-subnet-group \
  --backup-retention-period 30 \
  --multi-az \
  --storage-encrypted
```

#### ElastiCache Redis
```bash
# Create Redis subnet group
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name splitwise-redis-subnet-group \
  --cache-subnet-group-description "Subnet group for Splitwise Redis" \
  --subnet-ids subnet-12345 subnet-67890

# Create Redis cluster
aws elasticache create-replication-group \
  --replication-group-id splitwise-redis \
  --replication-group-description "Splitwise Redis cluster" \
  --num-cache-clusters 2 \
  --engine redis \
  --cache-node-type cache.t3.micro \
  --security-group-ids sg-12345 \
  --cache-subnet-group-name splitwise-redis-subnet-group \
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
  name: splitwise
```

#### ConfigMaps
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: splitwise-config
  namespace: splitwise
data:
  GIN_MODE: "release"
  PORT: "8080"
  DB_HOST: "splitwise-db.xxxx.us-east-1.rds.amazonaws.com"
  DB_PORT: "5432"
  DB_NAME: "splitwise_prod"
  DB_USER: "splitwise"
  DB_SSLMODE: "require"
  REDIS_HOST: "splitwise-redis.xxxxx.clustercfg.use1.cache.amazonaws.com"
  REDIS_PORT: "6379"
```

#### Secrets
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: splitwise-secrets
  namespace: splitwise
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
  name: splitwise
  namespace: splitwise
spec:
  replicas: 3
  selector:
    matchLabels:
      app: splitwise
  template:
    metadata:
      labels:
        app: splitwise
    spec:
      containers:
      - name: splitwise
        image: your-ecr-repo/splitwise:latest
        ports:
        - containerPort: 8080
        envFrom:
        - configMapRef:
            name: splitwise-config
        - secretRef:
            name: splitwise-secrets
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
  name: splitwise-service
  namespace: splitwise
spec:
  selector:
    app: splitwise
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
  name: splitwise-ingress
  namespace: splitwise
  annotations:
    kubernetes.io/ingress.class: "alb"
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS-1-2-2017-01
spec:
  tls:
  - hosts:
    - splitwise.yourdomain.com
    secretName: splitwise-tls
  rules:
  - host: splitwise.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: splitwise-service
            port:
              number: 80
```

#### Horizontal Pod Autoscaler
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: splitwise-hpa
  namespace: splitwise
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: splitwise
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
kubectl create namespace splitwise

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
kubectl get pods -n splitwise
kubectl get services -n splitwise
kubectl get ingress -n splitwise
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
        run: aws eks update-kubeconfig --name splitwise-cluster --region us-east-1
      
      - name: Build and push Docker image
        run: |
          # Build and push to ECR
          aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_REGISTRY
          docker build -t $ECR_REGISTRY/splitwise:$GITHUB_SHA .
          docker push $ECR_REGISTRY/splitwise:$GITHUB_SHA
      
      - name: Deploy to Kubernetes
        run: |
          # Update image in deployment
          kubectl set image deployment/splitwise splitwise=$ECR_REGISTRY/splitwise:$GITHUB_SHA -n splitwise
          kubectl rollout status deployment/splitwise -n splitwise
```

---

## Security Best Practices

### 1. Network Policies
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: splitwise-netpol
  namespace: splitwise
spec:
  podSelector:
    matchLabels:
      app: splitwise
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
  name: splitwise-psp
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
  name: splitwise-sa
  namespace: splitwise
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: splitwise-role
  namespace: splitwise
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: splitwise-rolebinding
  namespace: splitwise
subjects:
- kind: ServiceAccount
  name: splitwise-sa
  namespace: splitwise
roleRef:
  kind: Role
  name: splitwise-role
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
eksctl utils install-csi-driver --name splitwise-cluster --region us-east-1
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
  --set autoDiscovery.clusterName=splitwise-cluster \
  --set awsRegion=us-east-1
```

### 3. Spot Instances
```bash
# Create node group with spot instances
eksctl create nodegroup \
  --cluster splitwise-cluster \
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
   kubectl describe pod <pod-name> -n splitwise
   kubectl logs <pod-name> -n splitwise
   ```

2. **Service Not Accessible**
   ```bash
   kubectl get svc -n splitwise
   kubectl describe svc splitwise-service -n splitwise
   ```

3. **Ingress Not Working**
   ```bash
   kubectl get ingress -n splitwise
   kubectl describe ingress splitwise-ingress -n splitwise
   ```

4. **HPA Not Scaling**
   ```bash
   kubectl get hpa -n splitwise
   kubectl describe hpa splitwise-hpa -n splitwise
   ```

### Monitoring Commands
```bash
# Check cluster status
kubectl get nodes
kubectl get pods -A

# Check resource usage
kubectl top nodes
kubectl top pods -n splitwise

# Check events
kubectl get events -n splitwise --sort-by=.metadata.creationTimestamp
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

This Kubernetes approach provides excellent scalability, resilience, and operational efficiency for your Splitwise application on AWS.
