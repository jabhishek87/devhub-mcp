#!/bin/bash
# Deploy devhub-mcp gateway to Kubernetes
set -e

NAMESPACE="devhub"
IMAGE="devhub-mcp:latest"

echo "=== DevHub MCP Gateway - K8s Deploy ==="

# Build image (for local clusters like minikube/k3s)
echo "[1/4] Building image..."
docker build -t ${IMAGE} .

# Load image into local cluster if needed
if command -v minikube &>/dev/null && minikube status &>/dev/null; then
    echo "[2/4] Loading image into minikube..."
    minikube image load ${IMAGE}
elif command -v k3s &>/dev/null; then
    echo "[2/4] Importing image into k3s..."
    docker save ${IMAGE} | sudo k3s ctr images import -
else
    echo "[2/4] Assuming image is accessible to cluster..."
fi

# Apply manifests
echo "[3/4] Applying manifests..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/deployment.yaml

# Wait for rollout
echo "[4/4] Waiting for deployment..."
kubectl -n ${NAMESPACE} rollout status deployment/devhub-gateway --timeout=60s

echo ""
echo "=== Deployed ==="
kubectl -n ${NAMESPACE} get pods -l app=devhub-gateway
