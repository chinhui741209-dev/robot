# K3s Deployment Guide

## Overview

This directory contains K3s deployment configurations for the Robot POC system.

## Architecture

```
┌─────────────────────────────────────────────┐
│              K3s Cluster                    │
│              (Single Node)                  │
├─────────────────────────────────────────────┤
│  Namespace: robot                           │
├─────────────────────────────────────────────┤
│  Deployments:                               │
│  ├── hal-buddy (1 replica)                 │
│  ├── policy-node (1 replica)               │
│  ├── state-estimator (1 replica)           │
│  ├── recorder (1 replica)                  │
│  └── (more to come)                         │
├─────────────────────────────────────────────┤
│  Services:                                  │
│  ├── hal-buddy-svc                          │
│  ├── policy-svc                            │
│  └── (discovery via DNS)                   │
└─────────────────────────────────────────────┘
```

## Prerequisites

1. NVIDIA AGX Orin with Ubuntu 22.04
2. Docker installed
3. Root/sudo access

## Installation

### Option 1: K3s (Production)

```bash
# Run the installation script
sudo bash install_k3s.sh

# Or manual installation
curl -sfL https://get.k3s.io | sudo INSTALL_K3S_EXEC="--disable=traefik" sh -

# Set up kubectl
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# Verify
kubectl get nodes
kubectl get pods -A
```

### Option 2: Docker Compose (Development)

```bash
cd services/docker-compose
docker compose up -d
```

## Deploy Services

### K3s

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Deploy HAL
kubectl apply -f deploy-hal.yaml

# Deploy Policy
kubectl apply -f deploy-policy.yaml

# Check status
kubectl get pods -n robot
kubectl get svc -n robot
```

### Docker Compose

```bash
cd services/docker-compose
docker compose up -d

# Check status
docker ps
docker compose logs -f
```

## Comparison

| Feature | K3s | Docker Compose |
|---------|-----|---------------|
| Complexity | Medium | Low |
| Scalability | Multi-node | Single-node |
| Auto-healing | Yes | No |
| Load balancing | Yes | Limited |
| Production-ready | Yes | Dev only |
| Resource overhead | ~1GB | ~100MB |

## For Single-Node POC

**Recommendation**: Use Docker Compose for development/POC, migrate to K3s for production.

## Troubleshooting

```bash
# K3s logs
sudo journalctl -u k3s -f

# Docker Compose logs
docker compose logs -f <service>

# Check ROS topics
source /opt/ros/humble/setup.bash
ros2 topic list
```