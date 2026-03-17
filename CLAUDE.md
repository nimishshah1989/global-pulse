# CLAUDE.md — Momentum Compass: Global Relative Strength Engine
# JSL Wealth Platform — Standalone Module
# Last Updated: 2026-03-17

---

## PROJECT IDENTITY

**Product Name**: Momentum Compass
**Module Path**: momentum-compass/
**Platform**: JSL Wealth (jslwealth.com)
**Owner**: Nimish (solo operator, non-engineer — Claude builds everything)
**Design System**: Jhaveri Intelligence Platform (JIP) — light theme, teal primary, Inter font
**Philosophy**: Volume governs price. Price + Volume = Everything. Momentum investing, not value investing.

---

## WHAT THIS IS

A visual, interactive global relative strength tool that enables a momentum trader to:
1. See which countries in the world are attracting capital (and which are losing it)
2. Drill into strong countries to find their leading sectors
3. Drill into leading sectors to find the best individual stocks
4. Compare sectors across countries (which country's tech is strongest?)
5. Create baskets of instruments to simulate and track investment theses
6. Receive automated opportunity signals based on RS regime changes + volume confirmation

The tool covers ~25,000 instruments across US, UK, Japan, Hong Kong, India, South Korea, China, Taiwan, Australia, Brazil, Canada, Germany, France — sourced from Stooq (primary) and yfinance (gap-fill).

---

## CORE PHILOSOPHY — READ THIS FIRST

### The Mental Model
Global liquidity flows like water. It flows from weak markets to strong markets, from lagging sectors to leading sectors, from underperformers to outperformers. Volume is the width of the river — it tells you how much capital is actually flowing.

Relative Strength captures this flow numerically. An asset with rising RS and rising volume has institutional capital flowing in. An asset with falling RS and rising volume is being distributed. An asset with rising RS but falling volume is drifting up on thin air — it won't last.

### What This Tool Is NOT
- NOT a fundamental analysis tool (no earnings, no PE ratios, no balance sheets)
- NOT a prediction model (no ML, no forecasting — pattern recognition only)
- NOT a trading bot (it surfaces opportunities, humans make decisions)
- NOT a backtesting engine in the traditional sense (it tracks forward-looking baskets, not optimized backtests)

### The Scoring Must Be Foolproof
Every RS score, every ranking, every signal must be traceable to a simple, auditable formula. No black boxes. No arbitrary thresholds that can't be explained. A trader should be able to look at any recommendation and understand exactly WHY the system flagged it.

---

## DATA ARCHITECTURE

### Source Mapping — STRICT RULES

Every instrument has ONE canonical data source. No dual-sourcing. No fallbacks without explicit mapping.

**Stooq owns (PRIMARY — bulk CSV download from stooq.com/db/h/):**
```
US stocks:         NASDAQ (~4,300), NYSE (~3,550), NYSE MKT (~308)
US ETFs:           NASDAQ ETFs (~949), NYSE ETFs (~2,579)
UK stocks:         LSE (~2,010), LSE International (~3,487)
UK ETFs:           LSE ETFs (~4,196)
Japan stocks:      TSE (~3,957)
Japan ETFs:        TSE ETFs (~475)
Hong Kong stocks:  HKEX (~2,872)
Hong Kong ETFs:    HKEX ETFs (~195)
Global indices:    65 indices (^SPX, ^DJI, ^NKX, ^FTM, ^HSI, ^DAX, etc.)
Sector ETFs:       SPDR US sectors, iShares Global sectors, TOPIX sector ETFs
Country ETFs:      iShares country ETFs (EWJ, EWZ, FXI, INDA, EWT, EWY, etc.)
Currencies:        1,908 pairs
Bonds:             285 instruments
Commodities:       Via Barchart feed
Crypto:            220 via CoinAPI
Macroeconomic:     35+ countries
```

**yfinance owns (GAP-FILL — explicit instruments only):**
```
India:             NIFTY 50 (^NSEI), all NIFTY sector indices, NSE-listed stocks (.NS suffix)
South Korea:       KOSPI (^KS11), KOSPI 200 (^KS200), KRX sector data
China A-shares:    CSI 300 (000300.SS), SSE Composite (000001.SS), Shenzhen (399001.SZ)
Taiwan:            TWSE (^TWII), top TWSE constituents
Australia:         ASX 200 (^AXJO), ASX constituents
Brazil:            IBOVESPA (^BVSP), IBOV constituents
Canada:            TSX (^GSPTSE), TSX constituents
Global benchmark:  MSCI ACWI ETF (ACWI)
```

**The Mapping Table**: `data/instrument_map.json`
```json
{
  "instrument_id": "XLK_US",
  "name": "Technology Select Sector SPDR",
  "source": "stooq",
  "ticker_on_source": "XLK.US",
  "asset_type": "sector_etf",
  "country": "US",
  "sector": "technology",
  "benchmark": "^SPX",
  "hierarchy_level": 2,
  "liquidity_tier": 1,
  "currency": "USD"
}
```

If an instrument is not in this mapping table, it does not exist in the system. Period.

### Stooq Ticker Conventions
```
US stocks:        AAPL.US, MSFT.US, GOOG.US
UK stocks:        VOD.UK, HSBA.UK, BP..UK (note: some have double dots)
Japan stocks:     7203.JP (Toyota), 6758.JP (Sony)
Hong Kong stocks: 0005.HK (HSBC), 0700.HK (Tencent)
Indices:          ^SPX, ^DJI, ^NDQ, ^NKX, ^FTM, ^HSI, ^DAX, ^CAC
Sector ETFs:      XLK.US, XLF.US, IXN.US, 1615.JP
Country ETFs:     EWJ.US, EWZ.US, FXI.US, INDA.US
```

### Stooq CSV Download URL Pattern
```
https://stooq.com/q/d/l/?s={ticker}&d1={YYYYMMDD}&d2={YYYYMMDD}&i=d
```
Parameters: s=symbol, d1=start, d2=end, i=interval (d=daily, w=weekly, m=monthly)
Returns: CSV with columns Date,Open,High,Low,Close,Volume

### Stooq Bulk Download
From stooq.com/db/h/ — download entire regional databases as ZIP files.
Structure after unzip: data/{frequency}/{region}/{exchange} {type}/{subfolder}/
Each instrument is a separate CSV file named by ticker.

### yfinance Access Pattern
```python
import yfinance as yf
ticker = yf.Ticker("RELIANCE.NS")
hist = ticker.history(period="3y")  # Returns OHLCV DataFrame
```

### Data Refresh Schedule
- **Daily at 02:00 UTC**: Download latest day's data from Stooq CSV endpoint for all mapped instruments
- **Weekly on Sunday 06:00 UTC**: Full bulk download refresh from Stooq
- **Gap-fill markets (yfinance)**: Daily at 16:00 IST (after Indian market close)
- Store raw OHLCV in PostgreSQL. Never modify raw data. Compute RS scores in separate tables.

---

## RS ENGINE SPECIFICATION

### Stage 1: RS Ratio (Raw Relative Strength Line)

```python
RS_Line[t] = (Close_asset[t] / Close_benchmark[t]) * 100
```

Normalized to 100 at the start of the lookback window. When RS_Line rises, asset outperforms benchmark. When it falls, asset underperforms.

**Benchmark assignments (by hierarchy level):**
| Level | Asset Type | Benchmark |
|-------|-----------|-----------|
| 1 | Country index | MSCI ACWI (via ACWI ETF) |
| 2 | Sector index/ETF | Its country's primary index |
| 3 | Individual stock | Its sector index/ETF |
| Global Sector | iShares Global Sector ETF | MSCI ACWI |
| Cross-Country | Country ETF | User-selectable (ACWI, Gold, USD Cash) |

### Stage 2: RS Trend (Mansfield Relative Strength)

```python
RS_MA[t] = SMA(RS_Line, 150)  # 150 trading days ≈ 30 weeks
RS_Trend = "OUTPERFORMING" if RS_Line[t] > RS_MA[t] else "UNDERPERFORMING"
```

The 150-day SMA is the Stan Weinstein / Mansfield standard. It's slow enough to filter noise, fast enough to catch regime changes within 1-2 months.

### Stage 3: Percentile Rank (Normalized Score)

**DO NOT use z-scores. Use percentile rank.** Z-scores assume normal distribution which RS ratios violate. Percentile rank is distribution-agnostic.

For each asset, compute excess returns over its benchmark for each timeframe:

```python
Excess_Return_nM = (Asset_Return_nM - Benchmark_Return_nM)
```

Where nM ∈ {1M, 3M, 6M, 12M} and returns are simple price returns over the period.

Then rank within peer group:

```python
RS_Percentile_nM = percentile_rank(Excess_Return_nM, within=peer_group) 
# Returns 0-100, where 100 = best performer in group
```

**Peer groups:**
- Country indices: ranked against all 14 country indices
- Sectors within country: ranked against all sectors in that country (typically 10-12)
- Stocks within sector: ranked against all stocks in that sector

### Stage 4: Multi-Timeframe Composite

```python
RS_Composite = (
    RS_Percentile_1M  * 0.10 +
    RS_Percentile_3M  * 0.25 +
    RS_Percentile_6M  * 0.35 +   # Heaviest weight — primary momentum window
    RS_Percentile_12M * 0.30
)
```

Result: a 0-100 score where higher = stronger relative performer across all timeframes.

### Stage 5: RS Momentum (Rate of Change)

```python
RS_Momentum = RS_Composite[today] - RS_Composite[20 trading days ago]
```

Positive = RS is improving (getting stronger vs peers)
Negative = RS is deteriorating (getting weaker vs peers)

Normalize RS_Momentum to a -50 to +50 scale for consistent plotting:
```python
RS_Momentum_Normalized = clip(RS_Momentum, -50, +50)
```

### Stage 6: Volume Conviction Adjustment

```python
Volume_Ratio = SMA(Volume, 20) / SMA(Volume, 100)
```

Volume_Ratio > 1.0 means recent participation is above average (conviction).
Volume_Ratio < 1.0 means recent participation is below average (thinning).

**Adjustment multiplier (CONSERVATIVE — 0.85 to 1.15 range):**
```python
if Volume_Ratio >= 1.5:
    vol_multiplier = 1.15
elif Volume_Ratio >= 1.0:
    vol_multiplier = 1.0 + (Volume_Ratio - 1.0) * 0.30
elif Volume_Ratio >= 0.5:
    vol_multiplier = 1.0   # Neutral — don't penalize normal
else:
    vol_multiplier = 0.85  # Thin volume — discount signal

Adjusted_RS_Score = RS_Composite * vol_multiplier
```

**IMPORTANT**: For instruments with Liquidity Tier 3 (low volume), cap Adjusted_RS_Score at 70 regardless of raw score. Illiquid instruments cannot be top-ranked.

### Stage 7: Quadrant Classification (RRG Framework)

Plot each instrument on 2D plane:
- X-axis: Adjusted_RS_Score (0-100, centered at 50)
- Y-axis: RS_Momentum_Normalized (-50 to +50, centered at 0)

```
Quadrant determination:
  LEADING    = Adjusted_RS_Score > 50 AND RS_Momentum > 0
  WEAKENING  = Adjusted_RS_Score > 50 AND RS_Momentum <= 0
  LAGGING    = Adjusted_RS_Score <= 50 AND RS_Momentum <= 0
  IMPROVING  = Adjusted_RS_Score <= 50 AND RS_Momentum > 0
```

### Stage 8: Liquidity Tier Assignment

```python
avg_daily_value = SMA(Close * Volume, 20)  # 20-day average daily traded value

if avg_daily_value >= 5_000_000:    # $5M+ daily value
    liquidity_tier = 1               # Full confidence in all signals
elif avg_daily_value >= 500_000:    # $500K-$5M daily value
    liquidity_tier = 2               # Volume as supporting evidence only
else:
    liquidity_tier = 3               # Flag, don't rely on volume signals
    adjusted_rs_score = min(adjusted_rs_score, 70)  # Cap score
```

For non-USD instruments, convert to USD equivalent using the relevant currency pair from Stooq.

### Stage 9: Regime Filter (Global Risk Overlay)

```python
global_benchmark_price = ACWI_Close[today]
global_benchmark_ma200 = SMA(ACWI_Close, 200)

if global_benchmark_price < global_benchmark_ma200:
    regime = "RISK_OFF"
    # All opportunity signals get a warning flag
    # Recommendations shift from "buy leaders" to "identify survivors"
    # Basket suggestions favor defensive sectors (Utilities, Staples, Healthcare)
else:
    regime = "RISK_ON"
    # Normal operation — surface momentum leaders
```

### Stage 10: Extension Warning

```python
if RS_Percentile_3M > 95 and RS_Percentile_6M > 95 and RS_Percentile_12M > 90:
    extension_warning = True
    # Flag: "Extended — RS has been in top 5% across all timeframes"
    # Not a sell signal — a risk management nudge
```

---

## HIERARCHY LEVELS & INSTRUMENT UNIVERSE

### Level 1: Country Indices (14 Markets)

| Country | Index | Primary Source | Ticker | Country ETF (Stooq) |
|---------|-------|---------------|--------|---------------------|
| USA | S&P 500 | stooq | ^SPX | SPY.US |
| USA | NASDAQ 100 | stooq | ^NDQ | QQQ.US |
| UK | FTSE 100 | stooq | ^FTM | EWU.US |
| Germany | DAX 40 | stooq | ^DAX | EWG.US |
| France | CAC 40 | stooq | ^CAC | EWQ.US |
| Japan | Nikkei 225 | stooq | ^NKX | EWJ.US |
| Hong Kong | Hang Seng | stooq | ^HSI | EWH.US |
| China | CSI 300 | yfinance | 000300.SS | FXI.US / MCHI.US |
| South Korea | KOSPI | yfinance | ^KS11 | EWY.US |
| India | NIFTY 50 | yfinance | ^NSEI | INDA.US |
| Taiwan | TWSE | yfinance | ^TWII | EWT.US |
| Australia | ASX 200 | yfinance | ^AXJO | EWA.US |
| Brazil | IBOVESPA | yfinance | ^BVSP | EWZ.US |
| Canada | TSX | yfinance | ^GSPTSE | EWC.US |

**Global benchmark**: ACWI.US (iShares MSCI ACWI ETF) via yfinance
**Alternative benchmarks** (user-selectable): GLD.US (Gold), SHY.US (USD Cash proxy), EEM.US (EM), VEA.US (Developed ex-US)

### Level 2: Sector Indices/ETFs Per Country

#### USA — SPDR Sector ETFs (Stooq, Tier 1 liquidity)
XLK.US (Tech), XLF.US (Financials), XLV.US (Healthcare), XLY.US (Consumer Disc),
XLP.US (Consumer Staples), XLE.US (Energy), XLI.US (Industrials), XLB.US (Materials),
XLRE.US (Real Estate), XLU.US (Utilities), XLC.US (Communication Services)
**Benchmark**: ^SPX

#### India — NIFTY Sector Indices (yfinance)
^CNXIT (IT), ^NSEBANK (Bank), ^CNXFIN (Financial Services), ^CNXPHARMA (Pharma),
^CNXAUTO (Auto), ^CNXFMCG (FMCG), ^CNXMETAL (Metal), ^CNXREALTY (Realty),
^CNXENERGY (Energy), ^CNXINFRA (Infrastructure), ^CNXPSUBANK (PSU Bank)
**Benchmark**: ^NSEI

#### Japan — TOPIX Sector ETFs (Stooq, Tier 2 liquidity)
1615.JP (Banks), 1613.JP (Electrical Equip), 1617.JP (Foods), 1619.JP (Construction),
1621.JP (Pharma), 1622.JP (Transport Equip), 1623.JP (Iron/Steel), 1633.JP (Real Estate)
**Benchmark**: ^NKX

#### Hong Kong — HS Sub-Indices (yfinance) + HKEX ETFs (Stooq)
^HSTECH (HS Tech), ^HSFI (HS Finance), ^HSPI (HS Properties), ^HSUI (HS Utilities)
**Benchmark**: ^HSI

#### Global Cross-Country Sectors — iShares (Stooq, Tier 1-2 liquidity)
IXN.US (Global Tech), IXG.US (Global Finance), IXJ.US (Global Health),
IXC.US (Global Energy), EXI.US (Global Industrial), RXI.US (Global Cons Disc),
KXI.US (Global Cons Staples), JXI.US (Global Utilities), MXI.US (Global Materials),
IXP.US (Global Communication)
**Benchmark**: ACWI

#### Other Countries — Use Country ETF Sector Breakdown + Individual Stock GICS Tags
For UK, Germany, France, Korea, China, Taiwan, Australia, Brazil, Canada:
- Level 2 sector view uses iShares Global Sector ETFs as proxy
- Level 3 drill-down uses individual stocks tagged by GICS sector from constituent lists
- Over time, add country-specific sector ETFs as they become available on Stooq

### Level 3: Individual Stocks

**Constituent list sources:**
- S&P 500, NASDAQ 100, Dow Jones, DAX, FTSE 100, HSI, CSI 300/500: yfiua/index-constituents GitHub repo (auto-updated monthly, Yahoo Finance-compatible tickers)
- NIFTY 50 + all NIFTY sectors: NSE website downloads
- Nikkei 225, TOPIX 30: stooq.com/t/?i=589 and stooq.com/t/?i=581 (browseable, scrape to CSV)
- S&P 500 Sector Constituents: SPDR publishes daily holdings — use these for definitive sector→stock mapping

**Stock OHLCV**: From Stooq bulk download (US, UK, Japan, HK) or yfinance (India, Korea, others)

---

## DATABASE SCHEMA (PostgreSQL / Supabase)

### Core Tables

```sql
-- Master instrument registry
CREATE TABLE instruments (
    id TEXT PRIMARY KEY,              -- e.g. "AAPL_US", "XLK_US", "NIFTY50_IN"
    name TEXT NOT NULL,
    ticker_stooq TEXT,                -- Stooq ticker (NULL if yfinance-only)
    ticker_yfinance TEXT,             -- yfinance ticker (NULL if stooq-only)
    source TEXT NOT NULL CHECK (source IN ('stooq', 'yfinance')),
    asset_type TEXT NOT NULL,         -- 'country_index', 'sector_etf', 'sector_index', 'stock', 'country_etf', 'global_sector_etf', 'benchmark'
    country TEXT,                     -- ISO 2-letter: US, UK, JP, HK, IN, KR, CN, TW, AU, BR, CA, DE, FR
    sector TEXT,                      -- GICS sector slug: technology, financials, healthcare, etc.
    hierarchy_level INTEGER NOT NULL, -- 1=country, 2=sector, 3=stock
    benchmark_id TEXT REFERENCES instruments(id),  -- what it's measured against
    currency TEXT NOT NULL DEFAULT 'USD',
    liquidity_tier INTEGER DEFAULT 2 CHECK (liquidity_tier IN (1, 2, 3)),
    is_active BOOLEAN DEFAULT true,
    metadata JSONB                    -- extra info: index it belongs to, weight, etc.
);

-- Daily OHLCV price data (partitioned by year for performance)
CREATE TABLE prices (
    instrument_id TEXT NOT NULL REFERENCES instruments(id),
    date DATE NOT NULL,
    open NUMERIC(18,6),
    high NUMERIC(18,6),
    low NUMERIC(18,6),
    close NUMERIC(18,6) NOT NULL,
    volume BIGINT,
    PRIMARY KEY (instrument_id, date)
);

-- Daily computed RS scores (one row per instrument per day)
CREATE TABLE rs_scores (
    instrument_id TEXT NOT NULL REFERENCES instruments(id),
    date DATE NOT NULL,
    -- Raw RS data
    rs_line NUMERIC(12,4),            -- price/benchmark ratio × 100
    rs_ma_150 NUMERIC(12,4),          -- 150-day SMA of RS line
    rs_trend TEXT,                     -- 'OUTPERFORMING' or 'UNDERPERFORMING'
    -- Percentile ranks (within peer group)
    rs_pct_1m NUMERIC(5,2),           -- 0-100
    rs_pct_3m NUMERIC(5,2),
    rs_pct_6m NUMERIC(5,2),
    rs_pct_12m NUMERIC(5,2),
    -- Composite
    rs_composite NUMERIC(5,2),        -- weighted multi-TF score 0-100
    rs_momentum NUMERIC(6,2),         -- rate of change, -50 to +50
    -- Volume
    volume_ratio NUMERIC(6,3),        -- SMA20/SMA100 of volume
    vol_multiplier NUMERIC(4,3),      -- 0.85-1.15
    -- Final score
    adjusted_rs_score NUMERIC(5,2),   -- rs_composite × vol_multiplier, capped if tier 3
    quadrant TEXT,                     -- 'LEADING', 'WEAKENING', 'LAGGING', 'IMPROVING'
    liquidity_tier INTEGER,
    -- Flags
    extension_warning BOOLEAN DEFAULT false,
    regime TEXT DEFAULT 'RISK_ON',    -- 'RISK_ON' or 'RISK_OFF'
    PRIMARY KEY (instrument_id, date)
);

-- Constituent mapping (which stocks belong to which index/sector)
CREATE TABLE constituents (
    index_id TEXT NOT NULL REFERENCES instruments(id),
    stock_id TEXT NOT NULL REFERENCES instruments(id),
    as_of_date DATE NOT NULL,         -- when this mapping was valid
    weight NUMERIC(8,6),              -- weight in index (if available)
    PRIMARY KEY (index_id, stock_id, as_of_date)
);

-- User-created baskets
CREATE TABLE baskets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    benchmark_id TEXT REFERENCES instruments(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    weighting_method TEXT DEFAULT 'equal' CHECK (weighting_method IN ('equal', 'manual', 'rs_weighted'))
);

CREATE TABLE basket_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    basket_id UUID NOT NULL REFERENCES baskets(id),
    instrument_id TEXT NOT NULL REFERENCES instruments(id),
    weight NUMERIC(8,6) NOT NULL,     -- 0.0 to 1.0, all weights in basket sum to 1.0
    added_at TIMESTAMPTZ DEFAULT now(),
    removed_at TIMESTAMPTZ,           -- NULL if still active
    status TEXT DEFAULT 'active'
);

-- Daily basket NAV tracking (computed from position weights × instrument prices)
CREATE TABLE basket_nav (
    basket_id UUID NOT NULL REFERENCES baskets(id),
    date DATE NOT NULL,
    nav NUMERIC(14,6) NOT NULL,       -- normalized to 100 at creation
    benchmark_nav NUMERIC(14,6),      -- benchmark also normalized to 100
    rs_line NUMERIC(12,4),            -- basket RS vs benchmark
    PRIMARY KEY (basket_id, date)
);

-- Opportunity signals (auto-generated daily by RS engine)
CREATE TABLE opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id TEXT NOT NULL REFERENCES instruments(id),
    date DATE NOT NULL,
    signal_type TEXT NOT NULL,         -- see signal types below
    conviction_score NUMERIC(5,2),    -- 0-100
    description TEXT,
    metadata JSONB,                   -- quadrant, levels aligned, etc.
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### Signal Types for Opportunities Table
```
'quadrant_entry_leading'     -- Just entered LEADING quadrant
'quadrant_entry_improving'   -- Just entered IMPROVING quadrant (early signal)
'volume_breakout'            -- RS turning positive + volume > 1.5x average
'multi_level_alignment'      -- Country + Sector + Stock all in LEADING
'bearish_divergence'         -- Price new high, RS lower high
'bullish_divergence'         -- Price new low, RS higher low
'regime_change'              -- ACWI crossed above/below 200-day MA
'extension_alert'            -- Asset in top 5% across all timeframes
```

---

## FRONTEND ARCHITECTURE

### Tech Stack
- **React 18 + TypeScript** — strict mode, no any types
- **Vite** — build tool
- **Tailwind CSS** — following JIP Design System (see /mnt/skills/user/ui-design-system/SKILL.md)
- **Recharts** — RS line charts, bar charts, area charts
- **D3.js** — RRG scatter plots with animation (Recharts can't handle animated scatter with trails)
- **React-Simple-Maps** — world map choropleth (lightweight, no Mapbox dependency)
- **TanStack Table** — sortable, filterable data tables
- **React Router** — client-side routing between screens
- **Zustand** — lightweight state management (NOT Redux — too heavy for this)
- **date-fns** — date manipulation

### Design System Compliance
MANDATORY: Follow JIP UI Design System exactly. Key rules:
- Light theme ONLY — page bg slate-50, cards white, NEVER dark
- Teal-600 (#0d9488) primary brand color
- Inter font, font-mono for all financial numbers
- Emerald-600 for positive/profit, Red-600 for negative/loss
- Rounded-xl on cards, border-slate-200, no heavy shadows
- Emoji prefixes on page titles

**EXCEPTION for this module**: Since this is a global tool (not India-specific), number formatting uses INTERNATIONAL format ($1,234,567.89) not Indian format (₹1,23,45,678). Currency symbol matches the instrument's currency. Percentages always include +/- prefix.

### Screen Architecture (6 Screens)

#### Screen 1: 🌍 Global Pulse (World Map View)
**Route**: /compass
**Purpose**: "Where in the world is strength right now?"

Components:
- World choropleth map, countries colored by Adjusted_RS_Score (red=weak → green=strong)
- Rotation arrows on each country showing RS_Momentum direction
- Benchmark selector toggle: ACWI / MSCI World / MSCI EM / Gold / USD Cash
- Regime banner at top: "RISK ON" (green) or "RISK OFF" (red) based on ACWI vs 200-day MA
- Top 5 Strongest + Top 5 Weakest countries ticker strip at bottom
- RS Ranking table (sortable): Country | RS Score | Quadrant | 1M | 3M | 6M | 12M | Volume Ratio | Trend
- Click country → navigates to Screen 2

#### Screen 2: 📊 Country Deep Dive (Sector Rotation View)
**Route**: /compass/country/:countryCode
**Purpose**: "Which sectors are leading within this market?"

Components:
- RRG Scatter Plot (main visual): All sector ETFs for this country plotted on RS Score (x) vs RS Momentum (y)
  - Dots have 4-8 week trailing tails showing rotation trajectory
  - Animated playback with time slider
  - Quadrant lines at x=50, y=0
  - Color: LEADING=emerald, WEAKENING=amber, LAGGING=red, IMPROVING=blue
- Sector RS Ranking Table (left panel): Sector | RS Score | Quadrant | Vol Ratio | Trend | 1M/3M/6M/12M
- RS Line Chart (right panel): Selected sector's RS Line vs country benchmark, with 150-day MA overlay
  - Volume bars below RS line chart
- Breadcrumb: Global > [Country Name]
- Click sector → navigates to Screen 3

#### Screen 3: 🔍 Stock Selection (Constituent View)
**Route**: /compass/country/:countryCode/sector/:sectorSlug
**Purpose**: "Which stocks are leading this sector?"

Components:
- Stock RS Ranking Table (main): Ticker | Name | RS Score | Quadrant | RS Momentum | Vol Ratio | Liquidity | 1M/3M/6M/12M
  - Sortable by any column
  - Filter bar: Quadrant filter, Liquidity tier filter, RS minimum threshold slider
  - Extension warning badge on stocks flagged
- Mini RRG scatter for all stocks in sector (bottom panel)
- RS Line Chart + Price Chart (right panel, for selected stock):
  - Top: RS Line vs sector benchmark + 150-day MA
  - Bottom: Stock price candlestick/line + volume bars
  - Side-by-side or stacked layout
- Breadcrumb: Global > [Country] > [Sector]
- "Add to Basket" button on each stock row

#### Screen 4: 🔀 Sector Matrix (Cross-Country Comparison)
**Route**: /compass/matrix
**Purpose**: "Which country's [sector] is strongest?"

Components:
- Heat map matrix: Rows = Sectors (10-11), Columns = Countries (14)
- Each cell = Adjusted_RS_Score, colored red-yellow-green
- Click cell → jump to Screen 3 for that country+sector
- Column header = Country RS Score (so you see country strength + sector strength simultaneously)
- Row header = Global Sector RS Score (iShares Global Sector ETF score)
- Toggle: "Show Quadrant" mode (cells show quadrant label instead of score)
- Highlight row/column on hover for easy reading

#### Screen 5: 📦 Basket Builder & Simulator
**Route**: /compass/baskets and /compass/baskets/:basketId
**Purpose**: "Create, simulate, and track investment theses"

**Basket List View** (/compass/baskets):
- All baskets, sortable by creation date, return vs benchmark, RS score
- Quick stats: basket name, # instruments, creation date, return since inception, RS vs benchmark
- "Create New Basket" button

**Basket Detail View** (/compass/baskets/:basketId):
- Basket NAV chart vs benchmark (dual line, normalized to 100 at creation)
- RS Line of basket vs benchmark
- Contribution table: which positions are contributing/dragging
- Position list with individual RS scores and quadrants
- Performance stats: cumulative return, CAGR (if >1yr), max drawdown, Sharpe, % weeks outperforming
- "Add Position" / "Remove Position" actions
- "Compare with..." selector to overlay another basket

**Basket Creation Flow**:
1. Name + Description
2. Select benchmark from dropdown (ACWI, SPX, NIFTY, custom)
3. Add instruments (search bar that searches across all mapped instruments)
4. Assign weights (equal by default, manual override, or RS-weighted toggle)
5. Set start date (today for forward tracking, or past date for backtest)
6. On save: system computes NAV from start date to today using historical prices, then tracks forward daily

### Screen 6: 🎯 Opportunity Scanner
**Route**: /compass/opportunities
**Purpose**: "What should I be paying attention to today?"

Components:
- Signal feed (newest first): Date | Instrument | Signal Type | Conviction Score | Description
- Filter by: signal type, hierarchy level (country/sector/stock), conviction threshold, liquidity tier
- Multi-level alignment signals get PROMINENT display (card format, not table row)
  - Show the full chain: "🌍 India LEADING globally → 📊 NIFTY Metal LEADING in India → 🔍 Tata Steel LEADING in NIFTY Metal"
  - These are the highest-conviction outputs
- Regime change alerts at the top (if any)
- Click any opportunity → navigates to the relevant Screen 2 or 3

### Navigation
Sidebar navigation following JIP pattern:
```
🌍 Global Pulse
📊 Country Deep Dive (shows recently viewed countries)
🔀 Sector Matrix
📦 My Baskets
🎯 Opportunities
⚙️ Settings (benchmark preferences, liquidity filters, data refresh status)
```

Breadcrumb trail on every screen for hierarchy context.

---

## BACKEND ARCHITECTURE

### Tech Stack
- **Python 3.11+**
- **FastAPI** — REST API
- **SQLAlchemy** — ORM for PostgreSQL
- **pandas + numpy** — RS calculations
- **APScheduler** — cron jobs for daily data refresh + RS computation
- **httpx** — async HTTP client for Stooq CSV downloads
- **yfinance** — gap-fill data
- **Docker** — containerized deployment

### API Endpoints

```
# Data
GET /api/instruments                        — list all instruments (with filters)
GET /api/instruments/:id/prices             — OHLCV history
GET /api/instruments/:id/rs                 — RS score history

# Rankings
GET /api/rankings/countries                 — Level 1 country RS rankings
GET /api/rankings/sectors/:countryCode      — Level 2 sector rankings for country
GET /api/rankings/stocks/:countryCode/:sector — Level 3 stock rankings
GET /api/rankings/global-sectors            — Cross-country sector rankings
GET /api/matrix                             — Full country×sector matrix

# RRG Data
GET /api/rrg/countries                      — RRG scatter data for countries
GET /api/rrg/sectors/:countryCode           — RRG scatter data for sectors in country
GET /api/rrg/stocks/:countryCode/:sector    — RRG scatter data for stocks in sector
# Each returns: [{id, name, rs_score, rs_momentum, trail: [{date, rs_score, rs_momentum}]}]

# Baskets
POST /api/baskets                           — create basket
GET /api/baskets                            — list baskets
GET /api/baskets/:id                        — basket detail with NAV history
POST /api/baskets/:id/positions             — add position
DELETE /api/baskets/:id/positions/:posId    — remove position
GET /api/baskets/:id/performance            — performance metrics

# Opportunities
GET /api/opportunities                      — latest signals (filterable)
GET /api/opportunities/multi-level          — only multi-level alignment signals

# System
GET /api/regime                             — current RISK_ON/RISK_OFF status
GET /api/data-status                        — last refresh timestamps, data health
```

### Directory Structure
```
momentum-compass/
├── CLAUDE.md                    # THIS FILE
├── README.md                    # Setup & deployment guide
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                  # FastAPI app entry
│   ├── config.py                # Environment config
│   ├── db/
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── session.py           # DB connection
│   │   └── migrations/          # Alembic migrations
│   ├── data/
│   │   ├── instrument_map.json  # THE canonical mapping table
│   │   ├── constituents/        # CSV files of index→stock mappings
│   │   ├── stooq_fetcher.py     # Stooq CSV + bulk download
│   │   ├── yfinance_fetcher.py  # yfinance gap-fill
│   │   └── data_pipeline.py     # Orchestrates daily refresh
│   ├── engine/
│   │   ├── rs_calculator.py     # Stages 1-7 of RS engine
│   │   ├── volume_analyzer.py   # Stage 6 volume conviction
│   │   ├── regime_filter.py     # Stage 9 RISK_ON/OFF
│   │   ├── opportunity_scanner.py # Signal generation
│   │   └── basket_engine.py     # NAV calculation, performance
│   ├── api/
│   │   ├── rankings.py          # Ranking endpoints
│   │   ├── rrg.py               # RRG scatter data
│   │   ├── baskets.py           # Basket CRUD + performance
│   │   ├── opportunities.py     # Signal endpoints
│   │   └── system.py            # Health, regime, data status
│   └── jobs/
│       ├── daily_refresh.py     # Cron: download data + compute RS
│       └── scheduler.py         # APScheduler setup
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── store/               # Zustand stores
│   │   ├── api/                 # API client hooks
│   │   ├── components/
│   │   │   ├── layout/          # Sidebar, Breadcrumb, Header
│   │   │   ├── charts/          # RSLineChart, RRGScatter, VolumeChart
│   │   │   ├── maps/            # WorldChoropleth
│   │   │   ├── tables/          # RSRankingTable, BasketTable
│   │   │   └── common/          # QuadrantBadge, LiquidityBadge, RegimeBanner
│   │   └── screens/
│   │       ├── GlobalPulse.tsx
│   │       ├── CountryDeepDive.tsx
│   │       ├── StockSelection.tsx
│   │       ├── SectorMatrix.tsx
│   │       ├── BasketBuilder.tsx
│   │       └── OpportunityScanner.tsx
│   └── public/
└── data/                        # Local data cache (gitignored)
    ├── stooq_bulk/              # Unzipped Stooq bulk downloads
    └── cache/                   # Temporary processing files
```

---

## BUILD PHASES

### Phase 1: Data Foundation + RS Engine (No UI)
- Set up PostgreSQL schema
- Build instrument_map.json for all 14 countries + sectors + stocks
- Build Stooq fetcher (bulk download + daily CSV)
- Build yfinance fetcher (gap-fill markets)
- Build data_pipeline.py that populates prices table
- Build rs_calculator.py (Stages 1-8)
- Build regime_filter.py (Stage 9)
- Verify: run engine, spot-check RS scores against manual calculation
- **Deliverable**: Database populated, RS scores computed daily, verifiable via SQL queries

### Phase 2: Global Pulse + Country Deep Dive (First UI)
- Set up React + Vite + Tailwind (JIP design system)
- Build sidebar navigation
- Build FastAPI ranking + RRG endpoints
- Build Screen 1: World map + country rankings
- Build Screen 2: RRG scatter + sector rankings + RS line chart
- **Deliverable**: Trader can see global RS landscape and drill into any country's sectors

### Phase 3: Stock Selection + Sector Matrix
- Build Screen 3: Stock ranking table + individual RS charts
- Build Screen 4: Country × Sector heat map matrix
- Build opportunity_scanner.py (signal generation)
- Build Screen 6: Opportunity feed
- **Deliverable**: Full drill-down from country → sector → stock, plus automated signals

### Phase 4: Basket Builder & Simulator
- Build basket_engine.py (NAV computation, performance metrics)
- Build basket API endpoints
- Build Screen 5: Basket creation, tracking, comparison
- **Deliverable**: Complete tool — analysis + simulation + tracking

### Phase 5: Polish & Deploy
- Dark mode toggle (OPTIONAL — JIP standard is light, but traders prefer dark)
- Keyboard shortcuts (Vim-style: j/k navigation, Enter to drill in, Backspace to go up)
- CSV/PDF export for rankings and basket reports
- Mobile responsive layout
- Deploy to JSL Wealth AWS EC2 with Docker Compose + Nginx
- **Deliverable**: Production-ready deployment

---

## CODING STANDARDS

- Python: Black formatter, type hints everywhere, docstrings on all public functions
- TypeScript: strict mode, no `any`, explicit return types
- API responses: always include `{ data: ..., meta: { timestamp, count } }`
- Error handling: never crash silently — log errors, return clean error responses
- All financial calculations use Decimal (Python) or explicit rounding (never float imprecision)
- All dates in ISO 8601 format, all timestamps in UTC
- Git: conventional commits (feat:, fix:, data:, engine:, ui:)

---

## NON-NEGOTIABLE RULES

1. **Single source per instrument** — if it's not in instrument_map.json, it doesn't exist
2. **RS scores must be auditable** — every score traceable to formula + input data
3. **Volume cannot be faked** — if volume data is missing or unreliable, liquidity_tier = 3
4. **No black boxes** — every recommendation has a plain-English explanation
5. **Light theme by default** — JIP design system compliance
6. **Performance** — full RS computation for 25K instruments must complete in <5 minutes
7. **Data freshness** — stale data (>24h old) must be visually flagged in the UI
