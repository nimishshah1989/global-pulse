#!/bin/bash
# Deploy Momentum Compass to production (jslwealth server)
# Run from your Mac: ./deploy/deploy-prod.sh
#
# Prerequisites:
#   - SSH key at ~/.ssh/jsl-wealth-key.pem
#   - Data enriched locally (momentum_compass.db)
#
# What this script does:
#   1. Pushes code to GitHub
#   2. SSHs to server, pulls code
#   3. Transfers the SQLite DB (converted to SQL, imported to PostgreSQL)
#   4. Builds Docker containers
#   5. Sets up Nginx
#   6. Starts everything

set -e

SERVER="ubuntu@13.206.34.214"
SSH_KEY="$HOME/.ssh/jsl-wealth-key.pem"
PROJECT_DIR="/home/ubuntu/global-pulse"
BRANCH="claude/review-and-plan-architecture-6aWr1"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[DEPLOY]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

SSH_CMD="ssh -o StrictHostKeyChecking=no -i $SSH_KEY $SERVER"
SCP_CMD="scp -o StrictHostKeyChecking=no -i $SSH_KEY"

# Verify SSH key exists
[ -f "$SSH_KEY" ] || err "SSH key not found: $SSH_KEY"

# ── Step 1: Push latest code ──────────────────────────────────────────
log "Pushing latest code to GitHub..."
git push origin "$BRANCH" 2>/dev/null || true

# ── Step 2: Pull code on server ──────────────────────────────────────
log "Setting up code on server..."
$SSH_CMD << 'REMOTE_SETUP'
set -e

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "[DEPLOY] Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker ubuntu
fi

# Install docker-compose if not present
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "[DEPLOY] Installing docker-compose..."
    sudo apt-get update -qq && sudo apt-get install -y -qq docker-compose-plugin
fi

# Clone or pull repo
if [ -d /home/ubuntu/global-pulse ]; then
    cd /home/ubuntu/global-pulse
    git fetch origin
    git checkout claude/review-and-plan-architecture-6aWr1 2>/dev/null || git checkout -b claude/review-and-plan-architecture-6aWr1 origin/claude/review-and-plan-architecture-6aWr1
    git pull origin claude/review-and-plan-architecture-6aWr1
else
    cd /home/ubuntu
    git clone https://github.com/nimishshah1989/global-pulse.git
    cd global-pulse
    git checkout claude/review-and-plan-architecture-6aWr1
fi

echo "[DEPLOY] Code ready on server"
REMOTE_SETUP

# ── Step 3: Transfer SQLite data ──────────────────────────────────────
DB_PATH="$(dirname "$0")/../backend/momentum_compass.db"
if [ -f "$DB_PATH" ]; then
    DB_SIZE=$(du -sh "$DB_PATH" | cut -f1)
    log "Transferring database ($DB_SIZE)..."
    $SCP_CMD "$DB_PATH" "$SERVER:/home/ubuntu/global-pulse/backend/momentum_compass.db"
    log "Database transferred"
else
    warn "No local database found at $DB_PATH — server will use existing data"
fi

# ── Step 4: Set up environment + build ────────────────────────────────
log "Building and starting containers..."
$SSH_CMD << 'REMOTE_BUILD'
set -e
cd /home/ubuntu/global-pulse

# Create production .env if not exists
if [ ! -f backend/.env ]; then
    PGPASS=$(openssl rand -hex 16)
    cat > backend/.env << ENVEOF
DATABASE_URL=postgresql+asyncpg://compass:${PGPASS}@db:5432/momentum_compass
REDIS_URL=redis://redis:6379
APP_ENV=production
DATA_REFRESH_HOUR=2
ENVEOF
    echo "POSTGRES_PASSWORD=${PGPASS}" > .env
    echo "[DEPLOY] Created .env with generated credentials"
else
    echo "[DEPLOY] Using existing .env"
    # Ensure root .env has POSTGRES_PASSWORD
    if [ ! -f .env ]; then
        PGPASS=$(grep -oP 'compass:\K[^@]+' backend/.env || openssl rand -hex 16)
        echo "POSTGRES_PASSWORD=${PGPASS}" > .env
    fi
fi

# Build containers
docker compose build --no-cache

# Start database first
docker compose up -d db redis
echo "[DEPLOY] Waiting for PostgreSQL to be ready..."
sleep 10

# Import SQLite data into PostgreSQL if SQLite DB exists
if [ -f backend/momentum_compass.db ]; then
    echo "[DEPLOY] Importing data from SQLite to PostgreSQL..."

    # Get postgres password
    PGPASS=$(grep POSTGRES_PASSWORD .env | cut -d= -f2)

    # Export from SQLite
    python3 -c "
import sqlite3, csv, sys

db = sqlite3.connect('backend/momentum_compass.db')

# Export instruments
with open('/tmp/instruments.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['id','name','ticker_stooq','ticker_yfinance','source','asset_type','country','sector','hierarchy_level','benchmark_id','currency','liquidity_tier','is_active'])
    for row in db.execute('SELECT id,name,ticker_stooq,ticker_yfinance,source,asset_type,country,sector,hierarchy_level,benchmark_id,currency,liquidity_tier,is_active FROM instruments'):
        writer.writerow(row)

# Export prices
with open('/tmp/prices.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['instrument_id','date','open','high','low','close','volume'])
    for row in db.execute('SELECT instrument_id,date,open,high,low,close,volume FROM prices'):
        writer.writerow(row)

counts = db.execute('SELECT COUNT(*) FROM instruments').fetchone()[0]
pcounts = db.execute('SELECT COUNT(*) FROM prices').fetchone()[0]
print(f'Exported {counts} instruments, {pcounts} prices')
db.close()
" 2>/dev/null || echo "[DEPLOY] Python3 export skipped, will use Docker import"

    # Import to PostgreSQL via Docker
    docker cp /tmp/instruments.csv compass-db:/tmp/ 2>/dev/null || true
    docker cp /tmp/prices.csv compass-db:/tmp/ 2>/dev/null || true

    docker exec compass-db psql -U compass -d momentum_compass -c "
        CREATE TABLE IF NOT EXISTS instruments (
            id TEXT PRIMARY KEY, name TEXT NOT NULL,
            ticker_stooq TEXT, ticker_yfinance TEXT,
            source TEXT NOT NULL, asset_type TEXT NOT NULL,
            country TEXT, sector TEXT,
            hierarchy_level INTEGER NOT NULL,
            benchmark_id TEXT, currency TEXT NOT NULL DEFAULT 'USD',
            liquidity_tier INTEGER DEFAULT 2,
            is_active BOOLEAN DEFAULT true, metadata JSONB
        );
        CREATE TABLE IF NOT EXISTS prices (
            instrument_id TEXT NOT NULL,
            date DATE NOT NULL,
            open NUMERIC(18,6), high NUMERIC(18,6),
            low NUMERIC(18,6), close NUMERIC(18,6) NOT NULL,
            volume BIGINT,
            PRIMARY KEY (instrument_id, date)
        );
        CREATE TABLE IF NOT EXISTS rs_scores (
            instrument_id TEXT NOT NULL, date DATE NOT NULL,
            rs_line NUMERIC(12,4), rs_ma_150 NUMERIC(12,4), rs_trend TEXT,
            rs_pct_1m NUMERIC(5,2), rs_pct_3m NUMERIC(5,2),
            rs_pct_6m NUMERIC(5,2), rs_pct_12m NUMERIC(5,2),
            rs_composite NUMERIC(5,2), rs_momentum NUMERIC(6,2),
            volume_ratio NUMERIC(6,3), vol_multiplier NUMERIC(4,3),
            adjusted_rs_score NUMERIC(5,2), quadrant TEXT,
            liquidity_tier INTEGER,
            extension_warning BOOLEAN DEFAULT false,
            regime TEXT DEFAULT 'RISK_ON',
            PRIMARY KEY (instrument_id, date)
        );
    " 2>/dev/null

    # Copy CSVs into PostgreSQL
    docker exec compass-db psql -U compass -d momentum_compass -c "\COPY instruments FROM '/tmp/instruments.csv' WITH CSV HEADER" 2>/dev/null && \
        echo "[DEPLOY] Instruments imported" || echo "[DEPLOY] Instruments import skipped (may already exist)"

    docker exec compass-db psql -U compass -d momentum_compass -c "\COPY prices FROM '/tmp/prices.csv' WITH CSV HEADER" 2>/dev/null && \
        echo "[DEPLOY] Prices imported" || echo "[DEPLOY] Prices import skipped (may already exist)"
fi

# Also export rs_scores if they exist
if [ -f backend/momentum_compass.db ]; then
    python3 -c "
import sqlite3, csv
db = sqlite3.connect('backend/momentum_compass.db')
count = db.execute('SELECT COUNT(*) FROM rs_scores').fetchone()[0]
if count > 0:
    with open('/tmp/rs_scores.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['instrument_id','date','rs_line','rs_ma_150','rs_trend','rs_pct_1m','rs_pct_3m','rs_pct_6m','rs_pct_12m','rs_composite','rs_momentum','volume_ratio','vol_multiplier','adjusted_rs_score','quadrant','liquidity_tier','extension_warning','regime'])
        for row in db.execute('SELECT instrument_id,date,rs_line,rs_ma_150,rs_trend,rs_pct_1m,rs_pct_3m,rs_pct_6m,rs_pct_12m,rs_composite,rs_momentum,volume_ratio,vol_multiplier,adjusted_rs_score,quadrant,liquidity_tier,extension_warning,regime FROM rs_scores'):
            writer.writerow(row)
    print(f'Exported {count} RS scores')
else:
    print('No RS scores to export')
db.close()
" 2>/dev/null || true

    docker cp /tmp/rs_scores.csv compass-db:/tmp/ 2>/dev/null || true
    docker exec compass-db psql -U compass -d momentum_compass -c "\COPY rs_scores FROM '/tmp/rs_scores.csv' WITH CSV HEADER" 2>/dev/null && \
        echo "[DEPLOY] RS scores imported" || echo "[DEPLOY] RS scores import skipped"
fi

# Start all services
docker compose up -d

echo "[DEPLOY] All containers started"
docker compose ps
REMOTE_BUILD

# ── Step 5: Set up Nginx ──────────────────────────────────────────────
log "Configuring Nginx..."
$SSH_CMD << 'REMOTE_NGINX'
set -e

# Backup existing config
if [ -f /etc/nginx/sites-available/global-pulse ]; then
    sudo cp /etc/nginx/sites-available/global-pulse /etc/nginx/sites-available/global-pulse.bak.$(date +%Y%m%d)
fi

# Write Nginx config
sudo tee /etc/nginx/sites-available/global-pulse > /dev/null << 'NGINXCONF'
server {
    listen 80;
    server_name global-pulse.jslwealth.in;

    location /api/ {
        proxy_pass http://127.0.0.1:8011/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8011/health;
    }

    location / {
        proxy_pass http://127.0.0.1:8010/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

server {
    listen 80;
    server_name global-pulse-api.jslwealth.in;

    location / {
        proxy_pass http://127.0.0.1:8011/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINXCONF

# Enable site
sudo ln -sf /etc/nginx/sites-available/global-pulse /etc/nginx/sites-enabled/

# Test and reload
sudo nginx -t && sudo systemctl reload nginx
echo "[DEPLOY] Nginx configured and reloaded"
REMOTE_NGINX

# ── Step 6: Verify ───────────────────────────────────────────────────
log "Verifying deployment..."
sleep 5
$SSH_CMD "curl -s http://localhost:8011/health 2>/dev/null || echo 'Backend not responding yet (may need a few more seconds)'"
$SSH_CMD "curl -s http://localhost:8010/ >/dev/null 2>&1 && echo 'Frontend OK' || echo 'Frontend not ready yet'"
$SSH_CMD "docker compose -f /home/ubuntu/global-pulse/docker-compose.yml ps"

echo ""
log "=========================================="
log "DEPLOYMENT COMPLETE"
log "=========================================="
log "Frontend: http://global-pulse.jslwealth.in"
log "Backend:  http://global-pulse-api.jslwealth.in"
log "Health:   http://global-pulse-api.jslwealth.in/health"
log "=========================================="
