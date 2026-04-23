#!/bin/bash

# Orin CI/CD Setup Script
# This script automates the setup of GitHub Self-hosted Runner on Jetson Orin.

set -e

echo "--- Starting Orin CI/CD Setup ---"

# 1. Setup Sudoers for robot-core.service
echo "[Step 1/4] Setting up passwordless sudo for robot-core.service..."
SUDOERS_FILE="/etc/sudoers.d/robot-runner"
if [ ! -f "$SUDOERS_FILE" ]; then
    echo "nvidia ALL=(ALL) NOPASSWD: /bin/systemctl restart robot-core.service" | sudo tee $SUDOERS_FILE > /dev/null
    sudo chmod 0440 $SUDOERS_FILE
    echo "Sudoers file created at $SUDOERS_FILE"
else
    echo "Sudoers file already exists, skipping."
fi

# 2. Check Architecture
ARCH=$(uname -m)
if [ "$ARCH" != "aarch64" ]; then
    echo "Error: This script is intended for ARM64 (aarch64) architecture. Current: $ARCH"
    exit 1
fi

# 3. Download and Install Runner
RUNNER_DIR="$HOME/actions-runner"
if [ ! -d "$RUNNER_DIR" ]; then
    echo "[Step 2/4] Downloading GitHub Actions Runner..."
    mkdir -p "$RUNNER_DIR" && cd "$RUNNER_DIR"
    # Note: Using a recent version, GitHub will prompt to update if needed
    VERSION="2.316.1" 
    curl -o actions-runner-linux-arm64-${VERSION}.tar.gz -L https://github.com/actions/runner/releases/download/v${VERSION}/actions-runner-linux-arm64-${VERSION}.tar.gz
    tar xzf ./actions-runner-linux-arm64-${VERSION}.tar.gz
    echo "Runner downloaded and extracted to $RUNNER_DIR"
else
    echo "[Step 2/4] Runner directory already exists at $RUNNER_DIR, skipping download."
    cd "$RUNNER_DIR"
fi

# 4. Fetch Registration Token and Configure
echo ""
echo "[Step 3/4] Fetching runner registration token..."

REPO_OWNER="chinhui741209-dev"
REPO_NAME="robot"
REPO_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}"

echo "Using Repository: $REPO_URL"

# Prompt for PAT securely
read -s -p "Enter your GitHub Personal Access Token (PAT) with 'repo' scope: " GITHUB_PAT
echo ""

if [ -z "$GITHUB_PAT" ]; then
    echo "Error: PAT cannot be empty."
    exit 1
fi

echo "Calling GitHub API to get a short-lived registration token..."
API_RESPONSE=$(curl -sX POST -H "Authorization: token ${GITHUB_PAT}" \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runners/registration-token")

# Use Python3 (built-in on Jetson/Ubuntu) to extract the token from JSON safely
RUNNER_TOKEN=$(echo "$API_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)

if [ -z "$RUNNER_TOKEN" ]; then
    echo "Error: Failed to obtain registration token."
    echo "Please ensure your PAT is correct and has the 'repo' scope."
    echo "API Response: $API_RESPONSE"
    exit 1
fi

echo "Successfully obtained registration token!"

echo "Configuring the runner..."
./config.sh --url "$REPO_URL" --token "$RUNNER_TOKEN" --unattended --replace

# 5. Install as a Service
echo ""
echo "[Step 4/5] Installing runner as a system service..."
sudo ./svc.sh install nvidia
sudo ./svc.sh start

# 6. Configure GUI Autostart and Watchdog
echo ""
echo "[Step 5/5] Configuring GUI Autostart and Watchdog..."
mkdir -p "$HOME/.config/autostart"
chmod +x "$HOME/poc/poc-orin/gui/scripts/gui_watchdog.sh"
ln -sf "$HOME/poc/poc-orin/services/autostart/robot-gui.desktop" "$HOME/.config/autostart/"

echo ""
echo "--- Setup Complete! ---"
echo "1. Your Orin is connected to GitHub Actions."
echo "2. GUI Watchdog is configured to start on login."
echo "Please LOG OUT and LOG IN again to see the GUI."
echo ""
sudo ./svc.sh status
