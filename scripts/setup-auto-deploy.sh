#!/bin/bash
# ONE-TIME SETUP: Run this from your Mac to enable auto-deploy on EC2
# Usage: ./scripts/setup-auto-deploy.sh
#
# What it does:
# 1. Pulls latest code on EC2
# 2. Rebuilds and starts all containers
# 3. Installs a cron job that checks for new commits every 60 seconds
# 4. Auto-deploys whenever you push to the branch

set -euo pipefail

SERVER="13.206.34.214"
KEY="~/.ssh/jsl-wealth-key.pem"
PROJECT_DIR="/home/ubuntu/global-pulse"
BRANCH="claude/review-and-plan-architecture-6aWr1"
REPO="https://github.com/nimishshah1989/global-pulse.git"

echo "========================================="
echo "  Momentum Compass — Auto-Deploy Setup"
echo "========================================="
echo ""

# Step 1: Clone/pull and deploy
echo "[1/4] Syncing code to EC2..."
ssh -i "$KEY" ubuntu@"$SERVER" << REMOTE_SCRIPT
set -e

# Clone or pull
if [ -d "$PROJECT_DIR" ]; then
    cd "$PROJECT_DIR"
    git fetch origin
    git checkout "$BRANCH" 2>/dev/null || git checkout -b "$BRANCH" origin/"$BRANCH"
    git pull origin "$BRANCH"
else
    git clone -b "$BRANCH" "$REPO" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# Create env files
echo 'POSTGRES_PASSWORD=compass_secure_2026' > .env

if [ ! -f backend/.env ]; then
    cat > backend/.env << 'ENVEOF'
DATABASE_URL=postgresql+asyncpg://compass:compass_secure_2026@db:5432/momentum_compass
REDIS_URL=redis://redis:6379
STOOQ_BASE_URL=https://stooq.com/q/d/l/
DATA_REFRESH_HOUR=2
APP_ENV=production
ENVEOF
fi

echo "Code synced."
REMOTE_SCRIPT

echo ""
echo "[2/4] Building and starting containers..."
ssh -i "$KEY" ubuntu@"$SERVER" << REMOTE_SCRIPT
set -e
cd "$PROJECT_DIR"
docker compose build --no-cache
docker compose up -d
echo "Containers started."
REMOTE_SCRIPT

echo ""
echo "[3/4] Setting up auto-deploy cron..."
ssh -i "$KEY" ubuntu@"$SERVER" << 'REMOTE_SCRIPT'
set -e
PROJECT_DIR="/home/ubuntu/global-pulse"

# Make deploy script executable
chmod +x "$PROJECT_DIR/scripts/auto-deploy.sh"

# Install cron job — runs every minute, checks for new commits
CRON_CMD="* * * * * /bin/bash $PROJECT_DIR/scripts/auto-deploy.sh >> $PROJECT_DIR/deploy.log 2>&1"
(crontab -l 2>/dev/null | grep -v "auto-deploy.sh"; echo "$CRON_CMD") | crontab -
echo "Cron installed: auto-deploy checks every 60 seconds."
REMOTE_SCRIPT

echo ""
echo "[4/4] Verifying..."
sleep 15
ssh -i "$KEY" ubuntu@"$SERVER" << 'REMOTE_SCRIPT'
echo "Container status:"
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep compass
echo ""
echo "Backend health:"
curl -s http://localhost:8011/health
echo ""
echo "Latest commit:"
cd /home/ubuntu/global-pulse && git log --oneline -1
REMOTE_SCRIPT

echo ""
echo "========================================="
echo "  AUTO-DEPLOY IS NOW ACTIVE"
echo "========================================="
echo ""
echo "  Frontend: http://13.206.34.214:8010"
echo "  API:      http://13.206.34.214:8011"
echo ""
echo "  From now on, every git push to"
echo "  '$BRANCH'"
echo "  auto-deploys within 60 seconds."
echo "========================================="
