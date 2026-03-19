#!/bin/bash
# Auto-deploy script for Momentum Compass
# Runs as a systemd service on EC2, polls git every 60 seconds
# If new commits found, pulls and rebuilds

set -euo pipefail

PROJECT_DIR="/home/ubuntu/global-pulse"
BRANCH="claude/review-and-plan-architecture-6aWr1"
LOG_FILE="/home/ubuntu/global-pulse/deploy.log"
LOCK_FILE="/tmp/compass-deploy.lock"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Prevent concurrent deploys
if [ -f "$LOCK_FILE" ]; then
    log "Deploy already in progress, skipping"
    exit 0
fi

cd "$PROJECT_DIR" || exit 1

# Fetch latest
git fetch origin "$BRANCH" 2>/dev/null

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
    # No changes
    exit 0
fi

log "New commits detected: $LOCAL -> $REMOTE"
touch "$LOCK_FILE"

trap 'rm -f $LOCK_FILE' EXIT

# Pull changes
log "Pulling latest code..."
git checkout "$BRANCH" 2>/dev/null
git pull origin "$BRANCH"

# Determine what changed
CHANGED_FILES=$(git diff --name-only "$LOCAL" "$REMOTE")

REBUILD_FRONTEND=false
REBUILD_BACKEND=false

if echo "$CHANGED_FILES" | grep -q "^frontend/"; then
    REBUILD_FRONTEND=true
fi

if echo "$CHANGED_FILES" | grep -q "^backend/"; then
    REBUILD_BACKEND=true
fi

if echo "$CHANGED_FILES" | grep -q "docker-compose"; then
    REBUILD_FRONTEND=true
    REBUILD_BACKEND=true
fi

# Rebuild only what changed
if [ "$REBUILD_BACKEND" = true ]; then
    log "Rebuilding backend..."
    docker compose build backend --no-cache 2>&1 | tail -5 | tee -a "$LOG_FILE"
    docker compose up -d backend 2>&1 | tee -a "$LOG_FILE"
fi

if [ "$REBUILD_FRONTEND" = true ]; then
    log "Rebuilding frontend..."
    docker compose build frontend --no-cache 2>&1 | tail -5 | tee -a "$LOG_FILE"
    docker compose up -d frontend 2>&1 | tee -a "$LOG_FILE"
fi

# Re-compute RS scores after backend rebuild
if [ "$REBUILD_BACKEND" = true ]; then
    log "Running RS batch computation..."
    docker compose exec -T backend python -m scripts.compute_rs_batch 2>&1 | tail -10 | tee -a "$LOG_FILE" || log "WARN: RS batch computation failed"
fi

# Wait and verify
sleep 10
HEALTH=$(curl -s http://localhost:8011/health 2>/dev/null || echo '{"status":"error"}')
log "Deploy complete. Health: $HEALTH"
log "Deployed commit: $(git rev-parse --short HEAD)"
