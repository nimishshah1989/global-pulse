#!/bin/bash
set -euo pipefail

# Momentum Compass — One-command deploy to global-pulse.jslwealth.in
# Run from your Mac: ./deploy.sh

SERVER="13.206.34.214"
KEY="~/.ssh/jsl-wealth-key.pem"
SSH="ssh -i $KEY ubuntu@$SERVER"
PROJECT_DIR="/home/ubuntu/global-pulse"
REPO="https://github.com/nimishshah1989/global-pulse.git"
BRANCH="claude/review-and-plan-architecture-6aWr1"

echo "Deploying Momentum Compass to $SERVER..."

# Step 1: Clone or pull
echo "Syncing code..."
$SSH "if [ -d $PROJECT_DIR ]; then cd $PROJECT_DIR && git fetch origin && git checkout $BRANCH && git pull origin $BRANCH; else git clone -b $BRANCH $REPO $PROJECT_DIR; fi"

# Step 2: Create backend .env if not exists
echo "Setting up environment..."
$SSH "if [ ! -f $PROJECT_DIR/backend/.env ]; then
  cat > $PROJECT_DIR/backend/.env << 'ENVEOF'
DATABASE_URL=postgresql+asyncpg://compass:compass_secure_2026@db:5432/momentum_compass
REDIS_URL=redis://redis:6379
STOOQ_BASE_URL=https://stooq.com/q/d/l/
DATA_REFRESH_HOUR=2
APP_ENV=production
ENVEOF
fi"

# Step 3: Set postgres password
$SSH "cd $PROJECT_DIR && echo 'POSTGRES_PASSWORD=compass_secure_2026' > .env"

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
$SSH "if [ ! -f /etc/nginx/sites-available/global-pulse ]; then
  sudo cp /etc/nginx/sites-available/global-pulse /etc/nginx/sites-available/global-pulse.bak.\$(date +%Y%m%d) 2>/dev/null || true
  sudo cp $PROJECT_DIR/deploy/nginx-global-pulse.conf /etc/nginx/sites-available/global-pulse
  sudo ln -sf /etc/nginx/sites-available/global-pulse /etc/nginx/sites-enabled/
  sudo nginx -t && sudo systemctl reload nginx
  echo 'Nginx configured. Run certbot for SSL:'
  echo '  sudo certbot --nginx -d global-pulse.jslwealth.in'
else
  echo 'Nginx already configured.'
fi"

# Step 7: Seed database with sample data (first deploy)
echo "Seeding database..."
$SSH "cd $PROJECT_DIR && docker compose exec -T backend python scripts/seed_db.py" || echo "Seeding skipped (may already be seeded)"

# Step 7.5: Compute RS scores
echo "Computing RS scores..."
$SSH "cd $PROJECT_DIR && docker compose exec -T backend python -m scripts.compute_rs_batch" || echo "RS computation skipped"

# Step 8: Health check
echo "Running health check..."
HEALTH=$($SSH "curl -s http://localhost:8011/health" 2>/dev/null || echo '{"status":"error"}')
echo "Backend health: $HEALTH"

echo ""
echo "Deploy complete!"
echo "   Frontend: http://global-pulse.jslwealth.in"
echo "   Health:   http://global-pulse.jslwealth.in/health"
echo ""
echo "Next steps:"
echo "  1. SSL: sudo certbot --nginx -d global-pulse.jslwealth.in"
echo "  2. Fetch real data: docker compose exec backend python scripts/fetch_real_data.py"
echo "  3. Seed real data:  docker compose exec backend python -m scripts.seed_real_data"
