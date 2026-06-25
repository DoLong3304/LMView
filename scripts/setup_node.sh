#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# setup_node.sh — Bootstrap a new EC2 node for LMView Docker Swarm
# ─────────────────────────────────────────────────────────────────────────────
# This script installs Docker, configures EFS mount, and joins the node to
# an existing Docker Swarm cluster managed by the core/manager node.
#
# Usage:
#   export AWS_EFS_FS_ID="fs-xxxxxxxx"
#   export AWS_REGION="us-east-1"
#   export AWS_EFS_MOUNT_POINT="/mnt/efs"
#   bash scripts/setup_node.sh
#
# Or set defaults at the top of this script.
#
# After this script completes, log out and back in (or run ``newgrp docker``)
# so the Docker group membership takes effect.
# Then join the Swarm with the token from the manager node:
#   docker swarm join --token <SWARM_TOKEN> <MANAGER_IP>:2377
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Defaults — override with env vars ────────────────────────────────────────
EFS_FS_ID="${AWS_EFS_FS_ID:-fs-068ab00ace48b3585}"
AWS_REGION="${AWS_REGION:-ap-southeast-1}"
EFS_MOUNT_POINT="${AWS_EFS_MOUNT_POINT:-/mnt/efs}"

EFS_DNS_NAME="${EFS_FS_ID}.efs.${AWS_REGION}.amazonaws.com"
PROJECT_DIR="${EFS_MOUNT_POINT}/LMView"

echo "=========================================="
echo " LMView Node Setup"
echo " EFS FS ID : ${EFS_FS_ID}"
echo " Region    : ${AWS_REGION}"
echo " Mount     : ${EFS_MOUNT_POINT}"
echo " Project   : ${PROJECT_DIR}"
echo "=========================================="

# ── 1. Install system dependencies ───────────────────────────────────────────
echo ""
echo "[1/5] Installing system packages..."
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    nfs-common \
    docker.io \
    docker-compose-v2 \
    git \
    dnsutils \
    curl \
    jq

# ── 2. Configure Docker ─────────────────────────────────────────────────────
echo ""
echo "[2/5] Configuring Docker..."
sudo usermod -aG docker ubuntu
sudo systemctl enable docker
sudo systemctl start docker

# ── 3. Create EFS mount point ───────────────────────────────────────────────
echo ""
echo "[3/5] Preparing EFS mount..."
sudo mkdir -p "${EFS_MOUNT_POINT}"
sudo chown -R ubuntu:ubuntu "${EFS_MOUNT_POINT}"

FSTAB_ENTRY="${EFS_DNS_NAME}:/ ${EFS_MOUNT_POINT} nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport,_netdev 0 0"

if grep -q "${EFS_FS_ID}" /etc/fstab 2>/dev/null; then
    echo "  ✅ EFS entry already in /etc/fstab"
else
    echo "${FSTAB_ENTRY}" | sudo tee -a /etc/fstab > /dev/null
    echo "  ✅ Added EFS entry to /etc/fstab"
fi

# ── 4. Mount EFS ───────────────────────────────────────────────────────────
echo ""
echo "[4/5] Mounting EFS..."
sudo mount -a
MOUNT_OK=$(mount | grep -c "${EFS_FS_ID}" 2>/dev/null || true)
if [ "${MOUNT_OK}" -gt 0 ]; then
    echo "  ✅ EFS mounted at ${EFS_MOUNT_POINT}"
else
    echo "  ⚠️  EFS mount may have failed. Check 'mount | grep efs'"
fi

sudo chown -R ubuntu:ubuntu "${EFS_MOUNT_POINT}"

# ── 5. Verify project directory exists ─────────────────────────────────────
echo ""
echo "[5/5] Verifying project..."
if [ -d "${PROJECT_DIR}" ]; then
    echo "  ✅ Project directory found at ${PROJECT_DIR}"
    echo "  📄 Contents: $(ls -1 "${PROJECT_DIR}" | wc -l) items"
else
    echo "  ⚠️  Project directory ${PROJECT_DIR} not found."
    echo "     After joining the Swarm, clone the repo or mount it."
fi

# ── Done ───────────────────────────────────────────────────────────────────
echo ""
echo "=========================================="
echo " ✅ Setup Complete on $(hostname)!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Log out & back in (or: newgrp docker)"
echo "  2. Join the Swarm:"
echo "     docker swarm join --token <SWARM_TOKEN> <MANAGER_IP>:2377"
echo "  3. Verify: docker node ls"
echo ""
echo "If this is the FIRST core/manager node:"
echo "  docker swarm init --advertise-addr <PRIVATE_IP>"
echo ""
