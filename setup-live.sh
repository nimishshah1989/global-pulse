#!/bin/bash
set -euo pipefail

###############################################################################
# Momentum Compass — Full Production Setup
# Run ON the EC2 server: bash setup-live.sh
#
# This script handles EVERYTHING:
#   1. Stops/removes any conflicting old containers
#   2. Creates .env files
#   3. Builds and starts all Docker services
#   4. Waits for healthy services
#   5. Seeds instruments + sample data into PostgreSQL
#   6. Fetches REAL market data from Stooq + yfinance
#   7. Seeds real data + computes RS scores
#   8. Sets up Nginx reverse proxy
#   9. Obtains SSL certificate via Certbot
###############################################################################

DOMAIN="global-pulse.jslwealth.in"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
POSTGRES_PW="compass_secure_2026"

echo ""
echo "========================================"
echo "  Momentum Compass — Production Setup"
echo "  Domain: $DOMAIN"
echo "  Dir:    $PROJECT_DIR"
echo "========================================"
echo ""

cd "$PROJECT_DIR"

# ── Step 1: Clean up old containers ────────────────────────────────────
echo "[1/9] Cleaning up old containers..."
docker compose down 2>/dev/null || true
for name in compass-redis compass-db compass-backend compass-frontend; do
  if docker ps -a --format '{{.Names}}' | grep -q "^${name}$"; then
    echo "  Removing old container: $name"
    docker stop "$name" 2>/dev/null || true
    docker rm "$name" 2>/dev/null || true
  fi
done
echo "  Done."

# ── Step 2: Create environment files ──────────────────────────────────
echo "[2/9] Creating environment files..."

cat > .env << EOF
POSTGRES_PASSWORD=${POSTGRES_PW}
EOF

cat > backend/.env << EOF
DATABASE_URL=postgresql+asyncpg://compass:${POSTGRES_PW}@db:5432/momentum_compass
REDIS_URL=redis://redis:6379
STOOQ_BASE_URL=https://stooq.com/q/d/l/
DATA_REFRESH_HOUR=2
APP_ENV=production
EOF

echo "  .env and backend/.env created."

# ── Step 3: Build and start Docker services ───────────────────────────
echo "[3/9] Building Docker images (this may take a few minutes)..."
docker compose build

echo "  Starting services..."
docker compose up -d

# ── Step 4: Wait for services to be healthy ───────────────────────────
echo "[4/9] Waiting for services to become healthy..."
MAX_WAIT=120
ELAPSED=0

# Wait for database first
echo -n "  Waiting for PostgreSQL..."
until docker compose exec -T db pg_isready -U compass -d momentum_compass >/dev/null 2>&1; do
  sleep 2
  ELAPSED=$((ELAPSED + 2))
  echo -n "."
  if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
    echo " TIMEOUT"
    echo "ERROR: PostgreSQL did not become ready in ${MAX_WAIT}s"
    docker compose logs db
    exit 1
  fi
done
echo " Ready! (${ELAPSED}s)"

# Wait for backend
ELAPSED=0
echo -n "  Waiting for Backend API..."
until docker compose exec -T backend curl -sf http://localhost:8000/health >/dev/null 2>&1; do
  sleep 3
  ELAPSED=$((ELAPSED + 3))
  echo -n "."
  if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
    echo " TIMEOUT"
    echo "ERROR: Backend did not become ready in ${MAX_WAIT}s"
    docker compose logs backend
    exit 1
  fi
done
echo " Ready! (${ELAPSED}s)"

# Wait for frontend
ELAPSED=0
echo -n "  Waiting for Frontend..."
until docker compose exec -T frontend curl -sf http://localhost:80 >/dev/null 2>&1; do
  sleep 3
  ELAPSED=$((ELAPSED + 3))
  echo -n "."
  if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
    echo " TIMEOUT (non-critical, continuing)"
    break
  fi
done
echo " Ready! (${ELAPSED}s)"

echo ""
echo "  Container status:"
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'compass|NAMES'
echo ""

# ── Step 5: Seed instruments + sample data ────────────────────────────
echo "[5/9] Seeding instruments + sample data into PostgreSQL..."
docker compose exec -T backend python scripts/seed_db.py 2>&1 | tail -20
echo "  Seed complete."

# ── Step 6: Fetch REAL market data ────────────────────────────────────
echo "[6/9] Fetching REAL market data from Stooq + yfinance..."
echo "  This fetches ~2 years of OHLCV for all Level 1-2 instruments."
echo "  Stooq has rate limiting (2s between requests), so this takes a while."
echo ""
docker compose exec -T backend python scripts/fetch_real_data.py 2>&1 | tail -30
echo ""
echo "  Fetch complete."

# ── Step 7: Seed real data + compute RS scores ────────────────────────
echo "[7/9] Loading real data + computing RS scores..."
docker compose exec -T backend python -m scripts.seed_real_data 2>&1 | tail -20
echo "  RS scores computed."

# ── Step 8: Set up Nginx ──────────────────────────────────────────────
echo "[8/9] Setting up Nginx reverse proxy..."

# Backup existing config if present
if [ -f /etc/nginx/sites-available/global-pulse ]; then
  sudo cp /etc/nginx/sites-available/global-pulse "/etc/nginx/sites-available/global-pulse.bak.$(date +%Y%m%d%H%M%S)"
  echo "  Backed up existing Nginx config."
fi

sudo cp "$PROJECT_DIR/deploy/nginx-global-pulse.conf" /etc/nginx/sites-available/global-pulse
sudo ln -sf /etc/nginx/sites-available/global-pulse /etc/nginx/sites-enabled/

# Remove default site if it exists and might conflict
if [ -f /etc/nginx/sites-enabled/default ]; then
  echo "  (default site left in place)"
fi

echo "  Testing Nginx config..."
if sudo nginx -t 2>&1; then
  sudo systemctl reload nginx
  echo "  Nginx reloaded successfully."
else
  echo "ERROR: Nginx config test failed!"
  exit 1
fi

# ── Step 9: SSL Certificate ──────────────────────────────────────────
echo "[9/9] Obtaining SSL certificate..."
if command -v certbot >/dev/null 2>&1; then
  # Check if cert already exists
  if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    echo "  SSL certificate already exists for $DOMAIN"
  else
    echo "  Running certbot for $DOMAIN..."
    sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email nimish@jslwealth.com --redirect || {
      echo "  WARNING: Certbot failed. Site will work on HTTP only."
      echo "  You can retry manually: sudo certbot --nginx -d $DOMAIN"
    }
  fi
else
  echo "  WARNING: certbot not installed. Install with:"
  echo "    sudo apt install certbot python3-certbot-nginx"
  echo "  Then run: sudo certbot --nginx -d $DOMAIN"
fi

# ── Final verification ────────────────────────────────────────────────
echo ""
echo "========================================"
echo "  DEPLOYMENT COMPLETE"
echo "========================================"
echo ""
echo "  Services:"
docker ps --format '  {{.Names}}: {{.Status}}' | grep compass
echo ""

# Health check
HEALTH=$(curl -s http://localhost:8011/health 2>/dev/null || echo '{"status":"error"}')
echo "  Backend health: $HEALTH"

# Check data
echo ""
echo "  Quick data check:"
docker compose exec -T db psql -U compass -d momentum_compass -c "
  SELECT 'instruments' AS tbl, COUNT(*) AS rows FROM instruments
  UNION ALL
  SELECT 'prices', COUNT(*) FROM prices
  UNION ALL
  SELECT 'rs_scores', COUNT(*) FROM rs_scores
  UNION ALL
  SELECT 'opportunities', COUNT(*) FROM opportunities;
" 2>/dev/null || echo "  (Could not query DB directly)"

echo ""
echo "  Live at: https://$DOMAIN"
echo "  Health:  https://$DOMAIN/health"
echo ""
echo "  If SSL is not yet set up, access via:"
echo "    http://$DOMAIN"
echo ""
