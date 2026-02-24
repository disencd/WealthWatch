# Kubernetes deployment (DOKS / EKS)

This directory provides Kubernetes manifests for deploying WealthWatch.

## Cheapest DOKS option (Basic nodes, no Ingress / no LoadBalancer)

If you want the lowest-cost DOKS setup, use the `doks-basic` overlay. It:

- **Excludes** the Ingress resource (so you don't need an ingress controller)
- Uses the existing **ClusterIP** Service
- Sets the Deployment to **1 replica**

Access the app locally via port-forward (no public endpoint):

```bash
kubectl apply -k k8s/overlays/doks-basic
kubectl -n wealthwatch port-forward svc/wealthwatch 8080:80
```

Then open:

- http://localhost:8080

## What you must provide

- A container image registry (DOCR for DOKS, ECR for EKS, or any OCI registry)
- A PostgreSQL database (recommended: managed Postgres)
- An ingress controller (recommended: NGINX Ingress)

## Configure

Edit `k8s/base/app-configmap.yaml`:
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_SSLMODE`
- `PORT` should remain `8080`

Edit `k8s/base/app-secret.yaml`:
- `DB_USER`, `DB_PASSWORD`
- `JWT_SECRET`

Edit `k8s/base/app-ingress.yaml`:
- set `spec.rules[0].host` to your domain

Update the image in `k8s/base/app-deployment.yaml` (`spec.template.spec.containers[0].image`).

## Apply

Using Kustomize:

```bash
kubectl apply -k k8s/overlays/doks
kubectl apply -k k8s/overlays/doks-basic
# or
kubectl apply -k k8s/overlays/eks
```

## Notes

- The provided manifests assume an ingress class named `nginx`. If you use a different controller, update `ingressClassName`.
- Receipts are stored on the container filesystem by default. For production, mount a persistent volume or switch to object storage.
