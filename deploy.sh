#!/bin/bash
set -euo pipefail

# Momentum Compass — One-command deploy
# Run from your Mac: ./deploy.sh

SERVER="13.206.34.214"
KEY="~/.ssh/jsl-wealth-key.pem"
SSH="ssh -i $KEY ubuntu@$SERVER"
PROJECT_DIR="/home/ubuntu/momentum-compass"
REPO="https://github.com/nimishshah1989/global-pulse.git"
BRANCH="claude/review-and-plan-architecture-6aWr1"

echo "Deploying Momentum Compass to $SERVER..."

# Step 1: Clone or pull
echo "Syncing code..."
$SSH "if [ -d $PROJECT_DIR ]; then cd $PROJECT_DIR && git fetch origin && git checkout $BRANCH && git pull origin $BRANCH; else git clone -b $BRANCH $REPO $PROJECT_DIR; fi"

# Step 2: Create .env if not exists
echo "Setting up environment..."
$SSH "if [ ! -f $PROJECT_DIR/backend/.env ]; then
  cat > $PROJECT_DIR/backend/.env << 'ENVEOF'
DATABASE_URL=postgresql+asyncpg://compass:compass_secure_2024@db:5432/momentum_compass
REDIS_URL=redis://redis:6379
STOOQ_BASE_URL=https://stooq.com/q/d/l/
DATA_REFRESH_HOUR=2
APP_ENV=production
ENVEOF
fi"

# Step 3: Set postgres password
$SSH "cd $PROJECT_DIR && echo 'POSTGRES_PASSWORD=compass_secure_2024' > .env"

# Step 4: Build and start
echo "Building containers..."
$SSH "cd $PROJECT_DIR && docker compose build --no-cache"

echo "Starting services..."
$SSH "cd $PROJECT_DIR && docker compose up -d"

# Step 5: Wait and verify
echo "Waiting for services to start..."
sleep 20

echo "Checking service health..."
$SSH "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep compass"

# Step 6: Setup Nginx (first deploy only)
echo "Setting up Nginx..."
$SSH "if [ ! -f /etc/nginx/sites-available/compass.jslwealth.in ]; then
  sudo cp $PROJECT_DIR/nginx/compass.jslwealth.in.conf /etc/nginx/sites-available/compass.jslwealth.in
  sudo ln -sf /etc/nginx/sites-available/compass.jslwealth.in /etc/nginx/sites-enabled/
  sudo nginx -t && sudo systemctl reload nginx
  echo 'Nginx configured. Run certbot for SSL:'
  echo '  sudo certbot --nginx -d compass.jslwealth.in -d compass-api.jslwealth.in'
else
  echo 'Nginx already configured.'
fi"

# Step 7: Health check
echo "Running health check..."
HEALTH=$($SSH "curl -s http://localhost:8009/health" 2>/dev/null || echo '{"status":"error"}')
echo "Backend health: $HEALTH"

echo ""
echo "Deploy complete!"
echo "   Frontend: https://compass.jslwealth.in"
echo "   API:      https://compass-api.jslwealth.in"
echo "   Health:   https://compass-api.jslwealth.in/health"
