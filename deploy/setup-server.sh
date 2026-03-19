#!/bin/bash
# First-time server setup for Global Pulse on jslwealth EC2
# Run as: ssh -i ~/.ssh/jsl-wealth-key.pem ubuntu@13.206.34.214 'bash -s' < deploy/setup-server.sh
#
# Prerequisites: Docker + Docker Compose already installed on the server

set -euo pipefail

APP_DIR="/home/ubuntu/global-pulse"
REPO_URL="https://github.com/nimishshah1989/global-pulse.git"

echo "=== Global Pulse — Server Setup ==="

# 1. Clone repo
if [ -d "$APP_DIR" ]; then
    echo "App directory exists, pulling latest..."
    cd "$APP_DIR"
    git fetch origin
    git checkout claude/review-and-plan-architecture-6aWr1 2>/dev/null || true
    git pull origin claude/review-and-plan-architecture-6aWr1
else
    echo "Cloning repository..."
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

# 2. Generate production .env files
echo "Setting up environment files..."

if [ ! -f .env ]; then
    POSTGRES_PWD=$(openssl rand -hex 16)
    echo "POSTGRES_PASSWORD=${POSTGRES_PWD}" > .env
    echo "Generated root .env with POSTGRES_PASSWORD"
else
    POSTGRES_PWD=$(grep POSTGRES_PASSWORD .env | cut -d= -f2)
    echo "Root .env already exists"
fi

if [ ! -f backend/.env ]; then
    cat > backend/.env << ENVEOF
DATABASE_URL=postgresql+asyncpg://compass:${POSTGRES_PWD}@db:5432/momentum_compass
REDIS_URL=redis://redis:6379
STOOQ_BASE_URL=https://stooq.com/q/d/l/
DATA_REFRESH_HOUR=2
APP_ENV=production
ENVEOF
    echo "Generated backend/.env"
else
    echo "backend/.env already exists"
fi

# 3. Build and start containers
echo "Building Docker containers..."
docker compose build

echo "Starting services..."
docker compose up -d

# 4. Wait for health
echo "Waiting for services to initialize..."
sleep 25

echo "=== Container Status ==="
docker compose ps

# 4.5 Seed DB and compute RS scores
echo "Seeding database..."
docker compose exec -T backend python scripts/seed_db.py 2>/dev/null || echo "Seeding skipped (may already be seeded)"
echo "Computing RS scores..."
docker compose exec -T backend python -m scripts.compute_rs_batch 2>/dev/null || echo "RS computation skipped"

# 5. Health check
echo ""
echo "=== Health Check ==="
if curl -sf http://localhost:8011/health; then
    echo ""
    echo "Backend: HEALTHY"
else
    echo "Backend: UNHEALTHY — check logs with: docker compose logs backend"
fi

if curl -sf http://localhost:8010/ > /dev/null; then
    echo "Frontend: HEALTHY"
else
    echo "Frontend: UNHEALTHY — check logs with: docker compose logs frontend"
fi

# 6. Setup Nginx site config
echo ""
echo "=== Nginx Setup ==="
NGINX_CONF="/etc/nginx/sites-available/global-pulse"
if [ ! -f "$NGINX_CONF" ]; then
    echo "Copying Nginx config..."
    sudo cp deploy/nginx-global-pulse.conf "$NGINX_CONF"

    # For initial setup without SSL, use HTTP-only config first
    sudo tee /etc/nginx/sites-available/global-pulse-http << 'NGINXEOF'
server {
    listen 80;
    server_name global-pulse.jslwealth.in;

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8011;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8011/health;
        access_log off;
    }
}
NGINXEOF

    sudo ln -sf /etc/nginx/sites-available/global-pulse-http /etc/nginx/sites-enabled/global-pulse
    sudo nginx -t && sudo systemctl reload nginx
    echo "Nginx HTTP config active. Run certbot next for HTTPS."
    echo ""
    echo "To enable HTTPS, run:"
    echo "  sudo certbot --nginx -d global-pulse.jslwealth.in"
    echo "Then replace the Nginx config:"
    echo "  sudo cp $NGINX_CONF /etc/nginx/sites-available/global-pulse-http"
    echo "  sudo ln -sf /etc/nginx/sites-available/global-pulse /etc/nginx/sites-enabled/global-pulse"
    echo "  sudo nginx -t && sudo systemctl reload nginx"
else
    echo "Nginx config already exists at $NGINX_CONF"
fi

echo ""
echo "=== Setup Complete ==="
echo "App URL: http://global-pulse.jslwealth.in (after DNS propagation)"
echo "Direct:  http://13.206.34.214:8010 (frontend)"
echo "API:     http://13.206.34.214:8011/health (backend)"
echo ""
echo "Ports used:"
echo "  8011  → compass-backend (FastAPI)"
echo "  8010  → compass-frontend (Nginx+React)"
echo "  5433  → compass-db (PostgreSQL)"
echo "  6380  → compass-redis (Redis)"
