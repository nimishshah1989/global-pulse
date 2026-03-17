# Momentum Compass — Global Relative Strength Engine

**JSL Wealth Platform Module**

A visual, interactive global relative strength tool for momentum-driven investing. Covers ~25,000 instruments across 14 major markets. Identifies where global capital is flowing — from country level down to individual stocks — using price, volume, and multi-timeframe relative strength scoring.

---

## Philosophy

> Volume governs price. Price + Volume = Everything.

This tool does not predict. It observes capital flows through the lens of relative strength and volume, surfaces the strongest opportunities, and lets the trader decide. Every score is auditable. Every signal has a plain-English explanation. No black boxes.

---

## What It Does

1. **Global Pulse** — World map showing which countries are attracting capital (and which are losing it)
2. **Sector Rotation** — RRG (Relative Rotation Graph) showing sector leadership rotation within any country
3. **Stock Selection** — Rank stocks by RS within their sector, filtered by volume and liquidity
4. **Cross-Country Sectors** — Heat map comparing the same sector across different countries
5. **Basket Simulator** — Create instrument baskets, backtest, and track investment theses forward
6. **Opportunity Scanner** — Automated daily signals: quadrant changes, volume breakouts, multi-level alignment

---

## Data Sources

| Source | Coverage | Role |
|--------|----------|------|
| **Stooq** (stooq.com) | US, UK, Japan, Hong Kong stocks/ETFs. 65 global indices. Currencies, bonds, commodities. | Primary — ~80% of instruments |
| **yfinance** | India, South Korea, China, Taiwan, Australia, Brazil, Canada stocks/indices. MSCI ACWI benchmark. | Gap-fill — ~20% of instruments |

Every instrument has exactly ONE data source defined in `backend/data/instrument_map.json`. No dual-sourcing.

---

## Tech Stack

### Backend
- Python 3.11+
- FastAPI (REST API)
- PostgreSQL 15+ (data store)
- SQLAlchemy (ORM)
- pandas + numpy (RS calculations)
- APScheduler (daily cron jobs)
- Docker

### Frontend
- React 18 + TypeScript
- Vite (build)
- Tailwind CSS (JIP Design System — light theme, teal primary)
- Recharts (line/bar/area charts)
- D3.js (RRG animated scatter plots)
- React-Simple-Maps (world choropleth)
- TanStack Table (data tables)
- Zustand (state management)

---

## Prerequisites

- Docker & Docker Compose
- Node.js 18+ and npm (for frontend development)
- Python 3.11+ (for local backend development)
- PostgreSQL 15+ (or use Docker Compose managed instance)
- ~2GB disk space for Stooq bulk data downloads

---

## Quick Start (Docker Compose)

```bash
# Clone the repository
git clone <repo-url>
cd momentum-compass

# Copy environment template
cp .env.example .env
# Edit .env with your database credentials and any API keys

# Start everything
docker-compose up -d

# Run initial data load (first time only — takes ~15 minutes)
docker-compose exec backend python -m jobs.initial_load

# Verify data health
curl http://localhost:8000/api/data-status

# Frontend available at http://localhost:3000
# API available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

---

## Local Development Setup

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL database
createdb momentum_compass
# Or use Docker: docker run -d --name mc-postgres -p 5432:5432 -e POSTGRES_DB=momentum_compass -e POSTGRES_PASSWORD=secret postgres:15

# Run migrations
alembic upgrade head

# Seed instrument map
python -m data.seed_instruments

# Run initial data download + RS computation
python -m data.data_pipeline --full-refresh

# Start API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
# Available at http://localhost:5173 (Vite default)

# Build for production
npm run build
```

---

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/momentum_compass

# Stooq (no API key needed — uses public CSV endpoints)
STOOQ_BULK_DIR=/data/stooq_bulk       # Where to store bulk downloads
STOOQ_RATE_LIMIT_MS=200               # Delay between CSV requests (be polite)

# Data refresh schedule (cron expressions)
DAILY_REFRESH_CRON="0 2 * * *"        # 02:00 UTC daily
WEEKLY_BULK_CRON="0 6 * * 0"          # 06:00 UTC Sundays
INDIA_REFRESH_CRON="30 10 * * 1-5"    # 16:00 IST (10:30 UTC) on trading days

# Frontend
VITE_API_BASE_URL=http://localhost:8000/api
```

---

## Deployment (AWS EC2 — JSL Wealth)

### Server Setup

```bash
# On EC2 instance (same infrastructure as JSL Wealth)
# Assumes Docker and Docker Compose are installed

# Clone repo
cd /opt
git clone <repo-url> momentum-compass
cd momentum-compass

# Configure environment
cp .env.example .env
nano .env  # Set production DATABASE_URL, etc.

# Build and start
docker-compose -f docker-compose.prod.yml up -d --build

# Set up Nginx reverse proxy (add to existing JSL Wealth Nginx config)
# See nginx.conf in repo root
```

### Nginx Configuration

```nginx
# Add to existing JSL Wealth Nginx server block
location /compass/ {
    proxy_pass http://localhost:3000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}

location /compass/api/ {
    proxy_pass http://localhost:8000/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### GitHub Actions CI/CD

The repo includes `.github/workflows/deploy.yml` that:
1. Runs Python tests + TypeScript type checking
2. Builds Docker images
3. SSHs into EC2 and pulls + restarts containers

---

## Data Pipeline

### Daily Schedule

| Time (UTC) | Job | Duration |
|------------|-----|----------|
| 02:00 | Download latest Stooq daily data (US, UK, JP, HK) | ~5 min |
| 02:10 | Download yfinance gap-fill data (IN, KR, CN, TW, AU, BR, CA) | ~3 min |
| 02:15 | Compute RS scores for all instruments (Stages 1-10) | ~4 min |
| 02:20 | Run opportunity scanner (signal generation) | ~1 min |
| 02:22 | Update basket NAVs | ~1 min |
| 06:00 Sun | Full Stooq bulk download refresh | ~30 min |

### Manual Operations

```bash
# Force full data refresh
docker-compose exec backend python -m data.data_pipeline --full-refresh

# Refresh single instrument
docker-compose exec backend python -m data.data_pipeline --instrument AAPL_US

# Recompute RS scores without re-downloading data
docker-compose exec backend python -m engine.rs_calculator --recompute

# Update constituent lists from yfiua/index-constituents
docker-compose exec backend python -m data.update_constituents

# Health check
docker-compose exec backend python -m data.health_check
```

---

## RS Engine Overview

The engine computes 10 stages for every instrument daily:

| Stage | What | Output |
|-------|------|--------|
| 1 | RS Ratio (price / benchmark price) | RS Line value |
| 2 | RS Trend (RS Line vs 150-day SMA) | OUTPERFORMING / UNDERPERFORMING |
| 3 | Percentile Rank within peer group | 0-100 per timeframe (1M, 3M, 6M, 12M) |
| 4 | Multi-Timeframe Composite | Weighted score 0-100 |
| 5 | RS Momentum (rate of change) | -50 to +50 |
| 6 | Volume Conviction Adjustment | Multiplier 0.85-1.15 |
| 7 | Quadrant Classification | LEADING / WEAKENING / LAGGING / IMPROVING |
| 8 | Liquidity Tier | 1 (high) / 2 (moderate) / 3 (low) |
| 9 | Regime Filter | RISK_ON / RISK_OFF (based on ACWI vs 200-day MA) |
| 10 | Extension Warning | Flag if top 5% across all timeframes |

Full specification in CLAUDE.md.

---

## Project Structure

```
momentum-compass/
├── CLAUDE.md                    # Complete build specification (the source of truth)
├── README.md                    # This file
├── docker-compose.yml           # Development
├── docker-compose.prod.yml      # Production
├── nginx.conf                   # Nginx reverse proxy config
├── .env.example                 # Environment template
├── .github/workflows/
│   └── deploy.yml               # CI/CD pipeline
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                  # FastAPI app
│   ├── config.py
│   ├── db/                      # Models, migrations
│   ├── data/                    # Fetchers, pipeline, instrument map
│   ├── engine/                  # RS calculator, volume, regime, scanner
│   ├── api/                     # REST endpoints
│   └── jobs/                    # Scheduled tasks
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── src/
│       ├── components/          # Charts, maps, tables, common UI
│       ├── screens/             # 6 main screens
│       ├── store/               # Zustand state
│       └── api/                 # API client
└── data/                        # Local cache (gitignored)
```

---

## Build Sequence (Single Session)

Build everything in one session. Order matters — each step depends on the previous.

**Step 1 — Scaffold & Database**
- Init the project structure (backend + frontend)
- Set up PostgreSQL schema (all 7 tables)
- Create instrument_map.json with all instruments mapped

**Step 2 — Data Pipeline**
- Build Stooq fetcher (CSV endpoint for daily data)
- Build yfinance fetcher (gap-fill markets)
- Build data_pipeline.py orchestrator
- Run initial data load — populate prices table
- Verify: spot-check 5-10 instruments have correct OHLCV

**Step 3 — RS Engine**
- Build rs_calculator.py (all 10 stages)
- Build opportunity_scanner.py
- Run full RS computation
- Verify: spot-check RS scores, quadrant assignments

**Step 4 — API Layer**
- Build all FastAPI endpoints (rankings, RRG, baskets, opportunities)
- Verify: curl test each endpoint

**Step 5 — Frontend (All 6 Screens)**
- Scaffold React + Vite + Tailwind (JIP design system)
- Build sidebar navigation + routing
- Build Screen 1: Global Pulse (world map + country rankings)
- Build Screen 2: Country Deep Dive (RRG scatter + sector table + RS chart)
- Build Screen 3: Stock Selection (ranking table + filters + RS/price charts)
- Build Screen 4: Sector Matrix (country × sector heat map)
- Build Screen 5: Basket Builder (create, track, compare)
- Build Screen 6: Opportunity Scanner (signal feed)

**Step 6 — Wire & Verify**
- Connect frontend to API
- End-to-end test: Global Pulse → drill into US → drill into Tech → see NVDA RS
- Test basket creation and NAV tracking
- Test opportunity signals

Self-Learning Pattern Library is a future roadmap item, not part of initial build.

---

## Contributing

This is a solo-operator project. All code is written by Claude Code sessions guided by CLAUDE.md. When starting a new Claude Code session:

1. Read CLAUDE.md first — it is the single source of truth
2. Check current build phase status
3. Run `python -m data.health_check` to verify data state
4. Run existing tests before making changes
5. Follow the coding standards in CLAUDE.md (Black, strict TypeScript, conventional commits)

---

## License

Proprietary — JSL Wealth / Jhaveri Securities. Not open source.
