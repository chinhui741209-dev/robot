#!/bin/bash
# K3s Installation Script for NVIDIA Orin
# Run with: sudo bash install_k3s.sh

set -e

echo "=========================================="
echo "K3s Installation for Orin"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with sudo"
    exit 1
fi

# Check architecture
ARCH=$(uname -m)
if [ "$ARCH" != "aarch64" ]; then
    echo "Warning: This script is optimized for aarch64 (Orin)"
fi

echo "[1/4] Installing K3s (single node)..."
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--disable=traefik" sh -

echo "[2/4] Waiting for K3s to start..."
sleep 10

echo "[3/4] Checking K3s status..."
systemctl status k3s --no-pager || true

echo "[4/4] Getting node info..."
kubectl get nodes
kubectl get pods -A

echo ""
echo "=========================================="
echo "K3s Installation Complete"
echo "=========================================="
echo ""
echo "Config location: /etc/rancher/k3s/k3s.yaml"
echo ""
echo "To use kubectl:"
echo "  export KUBECONFIG=/etc/rancher/k3s/k3s.yaml"
echo "  kubectl get nodes"