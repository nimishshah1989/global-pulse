"""Generate comprehensive instrument_map.json from ETF classifier knowledge base.

This script produces the full instrument universe by:
1. Using ETFClassifier's KNOWN_ETFS for all hand-curated US-listed ETFs
2. Using KNOWN_INDICES for all Stooq indices
3. Preserving yfinance gap-fill instruments (India, Korea, China, etc.)
4. Adding all known JP/HK ETFs on Stooq

Run: python -m scripts.generate_instrument_map
"""

import json
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.etf_classifier import (
    COUNTRY_BENCHMARKS,
    COUNTRY_CURRENCY,
    ETFClassifier,
    KNOWN_ETFS,
    KNOWN_INDICES,
    build_instrument_entry,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "instrument_map.json"

# ── ETF name registry (ticker → full name) ─────────────────────────────
# These are the human-readable names for all known ETFs
ETF_NAMES: dict[str, str] = {
    # US broad market
    "SPY": "SPDR S&P 500 ETF Trust",
    "IVV": "iShares Core S&P 500 ETF",
    "VOO": "Vanguard S&P 500 ETF",
    "VTI": "Vanguard Total Stock Market ETF",
    "QQQ": "Invesco QQQ Trust",
    "DIA": "SPDR Dow Jones Industrial Average ETF",
    "IWM": "iShares Russell 2000 ETF",
    "IWB": "iShares Russell 1000 ETF",
    "IWF": "iShares Russell 1000 Growth ETF",
    "IWD": "iShares Russell 1000 Value ETF",
    "IWO": "iShares Russell 2000 Growth ETF",
    "IWN": "iShares Russell 2000 Value ETF",
    "IWS": "iShares Russell Midcap Value ETF",
    "IWP": "iShares Russell Midcap Growth ETF",
    "MDY": "SPDR S&P MidCap 400 ETF",
    "SLY": "SPDR S&P 600 SmallCap ETF",
    "RSP": "Invesco S&P 500 Equal Weight ETF",
    "SCHB": "Schwab US Broad Market ETF",
    "SCHA": "Schwab US Small-Cap ETF",
    "SCHD": "Schwab US Dividend Equity ETF",
    "IUSV": "iShares Core S&P US Value ETF",
    "IUSG": "iShares Core S&P US Growth ETF",
    # iShares MSCI single-country
    "EWU": "iShares MSCI United Kingdom ETF",
    "EWG": "iShares MSCI Germany ETF",
    "EWQ": "iShares MSCI France ETF",
    "EWJ": "iShares MSCI Japan ETF",
    "EWH": "iShares MSCI Hong Kong ETF",
    "FXI": "iShares China Large-Cap ETF",
    "MCHI": "iShares MSCI China ETF",
    "EWY": "iShares MSCI South Korea ETF",
    "INDA": "iShares MSCI India ETF",
    "EWT": "iShares MSCI Taiwan ETF",
    "EWA": "iShares MSCI Australia ETF",
    "EWZ": "iShares MSCI Brazil ETF",
    "EWC": "iShares MSCI Canada ETF",
    "EWS": "iShares MSCI Singapore ETF",
    "EWW": "iShares MSCI Mexico ETF",
    "EWP": "iShares MSCI Spain ETF",
    "EWI": "iShares MSCI Italy ETF",
    "EWN": "iShares MSCI Netherlands ETF",
    "EWD": "iShares MSCI Sweden ETF",
    "EWK": "iShares MSCI Belgium ETF",
    "EWO": "iShares MSCI Austria ETF",
    "EWL": "iShares MSCI Switzerland ETF",
    "EWM": "iShares MSCI Malaysia ETF",
    "EIDO": "iShares MSCI Indonesia ETF",
    "EPHE": "iShares MSCI Philippines ETF",
    "THD": "iShares MSCI Thailand ETF",
    "ECH": "iShares MSCI Chile ETF",
    "TUR": "iShares MSCI Turkey ETF",
    "EDEN": "iShares MSCI Denmark ETF",
    "ENZL": "iShares MSCI New Zealand ETF",
    "KSA": "iShares MSCI Saudi Arabia ETF",
    "QAT": "iShares MSCI Qatar ETF",
    "UAE": "iShares MSCI UAE ETF",
    "EIS": "iShares MSCI Israel ETF",
    "EFNL": "iShares MSCI Finland ETF",
    "NORW": "Global X MSCI Norway ETF",
    "EIRL": "iShares MSCI Ireland ETF",
    "GXG": "Global X MSCI Colombia ETF",
    "EPU": "iShares MSCI Peru ETF",
    "ARGT": "Global X MSCI Argentina ETF",
    "VNM": "VanEck Vietnam ETF",
    "NGE": "Global X MSCI Nigeria ETF",
    "GREK": "Global X MSCI Greece ETF",
    "EPOL": "iShares MSCI Poland ETF",
    "EZA": "iShares MSCI South Africa ETF",
    # Franklin FTSE single-country
    "FLAU": "Franklin FTSE Australia ETF",
    "FLBR": "Franklin FTSE Brazil ETF",
    "FLCA": "Franklin FTSE Canada ETF",
    "FLCH": "Franklin FTSE China ETF",
    "FLFR": "Franklin FTSE France ETF",
    "FLGB": "Franklin FTSE United Kingdom ETF",
    "FLGR": "Franklin FTSE Germany ETF",
    "FLHK": "Franklin FTSE Hong Kong ETF",
    "FLIN": "Franklin FTSE India ETF",
    "FLJP": "Franklin FTSE Japan ETF",
    "FLKR": "Franklin FTSE South Korea ETF",
    "FLMX": "Franklin FTSE Mexico ETF",
    "FLSA": "Franklin FTSE Saudi Arabia ETF",
    "FLSG": "Franklin FTSE Singapore ETF",
    "FLSW": "Franklin FTSE Switzerland ETF",
    "FLTW": "Franklin FTSE Taiwan ETF",
    # WisdomTree / other country
    "DXJ": "WisdomTree Japan Hedged Equity Fund",
    "DFJ": "WisdomTree Japan SmallCap Dividend Fund",
    "HEDJ": "WisdomTree Europe Hedged Equity Fund",
    "DFE": "WisdomTree Europe SmallCap Dividend Fund",
    "EPI": "WisdomTree India Earnings Fund",
    "CXSE": "WisdomTree China ex-State-Owned Enterprises Fund",
    "PIN": "Invesco India ETF",
    "INDY": "iShares India 50 ETF",
    "SMIN": "iShares MSCI India Small-Cap ETF",
    # Regional
    "EEM": "iShares MSCI Emerging Markets ETF",
    "VWO": "Vanguard FTSE Emerging Markets ETF",
    "IEMG": "iShares Core MSCI Emerging Markets ETF",
    "EFA": "iShares MSCI EAFE ETF",
    "VEA": "Vanguard FTSE Developed Markets ETF",
    "ACWI": "iShares MSCI ACWI ETF",
    "VT": "Vanguard Total World Stock ETF",
    "VXUS": "Vanguard Total International Stock ETF",
    "SCHF": "Schwab International Equity ETF",
    "SCHE": "Schwab Emerging Markets Equity ETF",
    "AAXJ": "iShares MSCI All Country Asia ex Japan ETF",
    "AIA": "iShares Asia 50 ETF",
    "EPP": "iShares MSCI Pacific ex Japan ETF",
    "EZU": "iShares MSCI Eurozone ETF",
    "FEZ": "SPDR EURO STOXX 50 ETF",
    "VGK": "Vanguard FTSE Europe ETF",
    "ILF": "iShares Latin America 40 ETF",
    "EEMA": "iShares MSCI Emerging Markets Asia ETF",
    "EMQQ": "EMQQ Emerging Markets Internet & Ecommerce ETF",
    "AFK": "VanEck Africa Index ETF",
    "FM": "iShares MSCI Frontier and Select EM ETF",
    "FRDM": "Freedom 100 Emerging Markets ETF",
    "IEUR": "iShares Core MSCI Europe ETF",
    "IPAC": "iShares Core MSCI Pacific ETF",
    # US Sectors — SPDR
    "XLK": "Technology Select Sector SPDR Fund",
    "XLF": "Financial Select Sector SPDR Fund",
    "XLV": "Health Care Select Sector SPDR Fund",
    "XLY": "Consumer Discretionary Select Sector SPDR Fund",
    "XLP": "Consumer Staples Select Sector SPDR Fund",
    "XLE": "Energy Select Sector SPDR Fund",
    "XLI": "Industrial Select Sector SPDR Fund",
    "XLB": "Materials Select Sector SPDR Fund",
    "XLRE": "Real Estate Select Sector SPDR Fund",
    "XLU": "Utilities Select Sector SPDR Fund",
    "XLC": "Communication Services Select Sector SPDR Fund",
    # US Sectors — Vanguard
    "VGT": "Vanguard Information Technology ETF",
    "VFH": "Vanguard Financials ETF",
    "VHT": "Vanguard Health Care ETF",
    "VDE": "Vanguard Energy ETF",
    "VIS": "Vanguard Industrials ETF",
    "VCR": "Vanguard Consumer Discretionary ETF",
    "VDC": "Vanguard Consumer Staples ETF",
    "VAW": "Vanguard Materials ETF",
    "VNQ": "Vanguard Real Estate ETF",
    "VPU": "Vanguard Utilities ETF",
    "VOX": "Vanguard Communication Services ETF",
    # US Sectors — iShares
    "IYW": "iShares US Technology ETF",
    "IYF": "iShares US Financials ETF",
    "IYH": "iShares US Healthcare ETF",
    "IYE": "iShares US Energy ETF",
    "IYJ": "iShares US Industrials ETF",
    "IYC": "iShares US Consumer Discretionary ETF",
    "IYK": "iShares US Consumer Staples ETF",
    "IDU": "iShares US Utilities ETF",
    "IYM": "iShares US Basic Materials ETF",
    "IYR": "iShares US Real Estate ETF",
    "IYZ": "iShares US Telecommunications ETF",
    # US Sectors — Fidelity
    "FREL": "Fidelity MSCI Real Estate Index ETF",
    "FENY": "Fidelity MSCI Energy Index ETF",
    "FHLC": "Fidelity MSCI Health Care Index ETF",
    "FDIS": "Fidelity MSCI Consumer Discretionary Index ETF",
    "FSTA": "Fidelity MSCI Consumer Staples Index ETF",
    "FIDU": "Fidelity MSCI Industrials Index ETF",
    "FMAT": "Fidelity MSCI Materials Index ETF",
    "FUTY": "Fidelity MSCI Utilities Index ETF",
    "FCOM": "Fidelity MSCI Communication Services Index ETF",
    "FTEC": "Fidelity MSCI Information Technology Index ETF",
    # Global Sectors — iShares
    "IXN": "iShares Global Tech ETF",
    "IXG": "iShares Global Financials ETF",
    "IXJ": "iShares Global Healthcare ETF",
    "IXC": "iShares Global Energy ETF",
    "EXI": "iShares Global Industrials ETF",
    "RXI": "iShares Global Consumer Discretionary ETF",
    "KXI": "iShares Global Consumer Staples ETF",
    "JXI": "iShares Global Utilities ETF",
    "MXI": "iShares Global Materials ETF",
    "IXP": "iShares Global Comm Services ETF",
    # Thematic / Sub-Sector
    "SOXX": "iShares Semiconductor ETF",
    "SMH": "VanEck Semiconductor ETF",
    "XSD": "SPDR S&P Semiconductor ETF",
    "IBB": "iShares Biotechnology ETF",
    "XBI": "SPDR S&P Biotech ETF",
    "IHI": "iShares US Medical Devices ETF",
    "XHB": "SPDR S&P Homebuilders ETF",
    "ITB": "iShares US Home Construction ETF",
    "XOP": "SPDR S&P Oil & Gas Exploration & Production ETF",
    "OIH": "VanEck Oil Services ETF",
    "KRE": "SPDR S&P Regional Banking ETF",
    "KBE": "SPDR S&P Bank ETF",
    "KIE": "SPDR S&P Insurance ETF",
    "XRT": "SPDR S&P Retail ETF",
    "ITA": "iShares US Aerospace & Defense ETF",
    "PPA": "Invesco Aerospace & Defense ETF",
    "XAR": "SPDR S&P Aerospace & Defense ETF",
    "HACK": "ETFMG Prime Cyber Security ETF",
    "CIBR": "First Trust NASDAQ Cybersecurity ETF",
    "WCLD": "WisdomTree Cloud Computing Fund",
    "SKYY": "First Trust Cloud Computing ETF",
    "AIQ": "Global X Artificial Intelligence & Technology ETF",
    "BOTZ": "Global X Robotics & Artificial Intelligence ETF",
    "ROBO": "ROBO Global Robotics & Automation Index ETF",
    "ARKK": "ARK Innovation ETF",
    "ARKG": "ARK Genomic Revolution ETF",
    "ARKW": "ARK Next Generation Internet ETF",
    "ARKF": "ARK Fintech Innovation ETF",
    "ARKQ": "ARK Autonomous Technology & Robotics ETF",
    "TAN": "Invesco Solar ETF",
    "ICLN": "iShares Global Clean Energy ETF",
    "QCLN": "First Trust NASDAQ Clean Edge Green Energy ETF",
    "PBW": "Invesco WilderHill Clean Energy ETF",
    "LIT": "Global X Lithium & Battery Tech ETF",
    "REMX": "VanEck Rare Earth/Strategic Metals ETF",
    "BLOK": "Amplify Transformational Data Sharing ETF",
    "BITO": "ProShares Bitcoin Strategy ETF",
    "IBIT": "iShares Bitcoin Trust ETF",
    "MJ": "Amplify Alternative Harvest ETF",
    "JETS": "US Global Jets ETF",
    "GAMR": "Wedbush ETFMG Video Game Tech ETF",
    "ESPO": "VanEck Video Gaming and eSports ETF",
    # China sectors (US-listed)
    "KWEB": "KraneShares CSI China Internet ETF",
    "CHIQ": "Global X MSCI China Consumer Discretionary ETF",
    "CQQQ": "Invesco China Technology ETF",
    "KURE": "KraneShares MSCI All China Health Care Index ETF",
    "KGRN": "KraneShares MSCI China Clean Technology Index ETF",
    "CHIS": "Global X MSCI China Consumer Staples ETF",
    "CHIH": "Global X MSCI China Health Care ETF",
    "CHII": "Global X MSCI China Industrials ETF",
    "CHIF": "Global X MSCI China Financials ETF",
    "CHIE": "Global X MSCI China Energy ETF",
    "CHIM": "Global X MSCI China Materials ETF",
    "CHIR": "Global X MSCI China Real Estate ETF",
    # Commodities
    "GLD": "SPDR Gold Shares",
    "IAU": "iShares Gold Trust",
    "SLV": "iShares Silver Trust",
    "GDX": "VanEck Gold Miners ETF",
    "GDXJ": "VanEck Junior Gold Miners ETF",
    "USO": "United States Oil Fund",
    "UNG": "United States Natural Gas Fund",
    "DBA": "Invesco DB Agriculture Fund",
    "DBC": "Invesco DB Commodity Index Tracking Fund",
    "PDBC": "Invesco Optimum Yield Diversified Commodity Strategy No K-1 ETF",
    "PPLT": "abrdn Physical Platinum Shares ETF",
    "PALL": "abrdn Physical Palladium Shares ETF",
    "COPX": "Global X Copper Miners ETF",
    "SIL": "Global X Silver Miners ETF",
    "URA": "Global X Uranium ETF",
    "WEAT": "Teucrium Wheat Fund",
    "CORN": "Teucrium Corn Fund",
    # Fixed Income
    "AGG": "iShares Core US Aggregate Bond ETF",
    "BND": "Vanguard Total Bond Market ETF",
    "TLT": "iShares 20+ Year Treasury Bond ETF",
    "IEF": "iShares 7-10 Year Treasury Bond ETF",
    "SHY": "iShares 1-3 Year Treasury Bond ETF",
    "TIPS": "SPDR Portfolio TIPS ETF",
    "TIP": "iShares TIPS Bond ETF",
    "LQD": "iShares iBoxx $ Investment Grade Corporate Bond ETF",
    "HYG": "iShares iBoxx $ High Yield Corporate Bond ETF",
    "JNK": "SPDR Bloomberg High Yield Bond ETF",
    "MBB": "iShares MBS ETF",
    "VCSH": "Vanguard Short-Term Corporate Bond ETF",
    "VCIT": "Vanguard Intermediate-Term Corporate Bond ETF",
    "VGSH": "Vanguard Short-Term Treasury ETF",
    "VGIT": "Vanguard Intermediate-Term Treasury ETF",
    "VGLT": "Vanguard Long-Term Treasury ETF",
    "EMB": "iShares JP Morgan USD Emerging Markets Bond ETF",
    "PCY": "Invesco Emerging Markets Sovereign Debt ETF",
    "BWX": "SPDR Bloomberg International Treasury Bond ETF",
    "BNDX": "Vanguard Total International Bond ETF",
    "IGOV": "iShares International Treasury Bond ETF",
    "IAGG": "iShares Core International Aggregate Bond ETF",
    "MUB": "iShares National Muni Bond ETF",
    "HYD": "VanEck High Yield Muni ETF",
    "SPTL": "SPDR Portfolio Long Term Treasury ETF",
    "SPTI": "SPDR Portfolio Intermediate Term Treasury ETF",
    "SPTS": "SPDR Portfolio Short Term Treasury ETF",
    "FLOT": "iShares Floating Rate Bond ETF",
    "BKLN": "Invesco Senior Loan ETF",
    "SRLN": "SPDR Blackstone Senior Loan ETF",
    "TMF": "Direxion Daily 20+ Year Treasury Bull 3X Shares",
    "TBT": "ProShares UltraShort 20+ Year Treasury",
}

# Index names from KNOWN_INDICES
INDEX_NAMES: dict[str, str] = {
    k: v["name"] for k, v in KNOWN_INDICES.items()
}

# ── JAPAN TOPIX Sector ETFs (Stooq .JP suffix) ─────────────────────────
JAPAN_SECTOR_ETFS: list[dict] = [
    {"ticker": "1615.JP", "name": "TOPIX Banks ETF", "sector": "banks"},
    {"ticker": "1613.JP", "name": "TOPIX Electrical Equipment ETF", "sector": "electrical_equipment"},
    {"ticker": "1617.JP", "name": "TOPIX Foods ETF", "sector": "foods"},
    {"ticker": "1619.JP", "name": "TOPIX Construction ETF", "sector": "construction"},
    {"ticker": "1621.JP", "name": "TOPIX Pharma ETF", "sector": "pharma"},
    {"ticker": "1622.JP", "name": "TOPIX Transport Equipment ETF", "sector": "transport_equipment"},
    {"ticker": "1623.JP", "name": "TOPIX Iron/Steel ETF", "sector": "iron_steel"},
    {"ticker": "1633.JP", "name": "TOPIX Real Estate ETF", "sector": "real_estate"},
    {"ticker": "1618.JP", "name": "TOPIX Energy Resources ETF", "sector": "energy"},
    {"ticker": "1620.JP", "name": "TOPIX Chemicals ETF", "sector": "chemicals"},
    {"ticker": "1624.JP", "name": "TOPIX Nonferrous Metals ETF", "sector": "nonferrous_metals"},
    {"ticker": "1625.JP", "name": "TOPIX Machinery ETF", "sector": "machinery"},
    {"ticker": "1626.JP", "name": "TOPIX Precision Instruments ETF", "sector": "precision_instruments"},
    {"ticker": "1627.JP", "name": "TOPIX Other Manufacturing ETF", "sector": "other_manufacturing"},
    {"ticker": "1628.JP", "name": "TOPIX Commerce/Wholesale ETF", "sector": "commerce"},
    {"ticker": "1629.JP", "name": "TOPIX Commerce/Retail ETF", "sector": "retail"},
    {"ticker": "1630.JP", "name": "TOPIX Securities ETF", "sector": "securities"},
    {"ticker": "1631.JP", "name": "TOPIX Insurance ETF", "sector": "insurance"},
    {"ticker": "1632.JP", "name": "TOPIX Other Finance ETF", "sector": "other_finance"},
    {"ticker": "1634.JP", "name": "TOPIX Transportation ETF", "sector": "transportation"},
    {"ticker": "1635.JP", "name": "TOPIX IT/Communication ETF", "sector": "technology"},
    {"ticker": "1636.JP", "name": "TOPIX Services ETF", "sector": "services"},
    {"ticker": "1610.JP", "name": "TOPIX ETF", "sector": None},
    {"ticker": "1329.JP", "name": "iShares Nikkei 225 ETF", "sector": None},
    {"ticker": "1306.JP", "name": "TOPIX ETF (Nomura)", "sector": None},
    {"ticker": "1321.JP", "name": "Nikkei 225 ETF (Nomura)", "sector": None},
    {"ticker": "1330.JP", "name": "Nikkei 225 ETF (Nikko)", "sector": None},
    {"ticker": "1346.JP", "name": "MAXIS Nikkei 225 ETF", "sector": None},
    {"ticker": "1348.JP", "name": "MAXIS TOPIX ETF", "sector": None},
    {"ticker": "2516.JP", "name": "MAXIS TOPIX-17 ETF", "sector": None},
    {"ticker": "1308.JP", "name": "Listed Index Fund TOPIX", "sector": None},
]

# ── HK ETFs on Stooq (.HK suffix) ──────────────────────────────────────
HK_ETFS: list[dict] = [
    {"ticker": "2800.HK", "name": "Tracker Fund of Hong Kong", "sector": None, "country": "HK"},
    {"ticker": "2833.HK", "name": "Hang Seng Index ETF", "sector": None, "country": "HK"},
    {"ticker": "2828.HK", "name": "Hang Seng H-Share Index ETF", "sector": "h_shares", "country": "CN"},
    {"ticker": "3067.HK", "name": "iShares Hang Seng TECH ETF", "sector": "technology", "country": "HK"},
    {"ticker": "3033.HK", "name": "CSOP Hang Seng TECH Index ETF", "sector": "technology", "country": "HK"},
    {"ticker": "2823.HK", "name": "iShares FTSE A50 China ETF", "sector": None, "country": "CN"},
    {"ticker": "2822.HK", "name": "CSOP FTSE China A50 ETF", "sector": None, "country": "CN"},
    {"ticker": "3188.HK", "name": "ChinaAMC CSI 300 Index ETF", "sector": None, "country": "CN"},
    {"ticker": "2801.HK", "name": "iShares Core MSCI China ETF", "sector": None, "country": "CN"},
    {"ticker": "3040.HK", "name": "Samsung CSI China Dragon Internet ETF", "sector": "technology", "country": "CN"},
    {"ticker": "2836.HK", "name": "iShares India Nifty 50 ETF (HK)", "sector": None, "country": "IN"},
    {"ticker": "3010.HK", "name": "iShares Asia ex-Japan ETF (HK)", "sector": None, "country": None},
    {"ticker": "2813.HK", "name": "Samsung S&P GSCI Crude Oil ETF", "sector": "crude_oil", "country": None},
    {"ticker": "2840.HK", "name": "SPDR Gold Trust (HK)", "sector": "gold", "country": None},
    {"ticker": "3081.HK", "name": "Value Gold ETF (HK)", "sector": "gold", "country": None},
]

# ── yfinance gap-fill instruments (preserve existing) ──────────────────
# These markets are NOT on Stooq, so we keep them via yfinance
YFINANCE_INSTRUMENTS: list[dict] = [
    # Global benchmark
    {"id": "ACWI", "name": "iShares MSCI ACWI ETF", "ticker_yfinance": "ACWI", "asset_type": "benchmark", "country": None, "sector": None, "hierarchy_level": 1, "benchmark_id": None, "currency": "USD", "liquidity_tier": 1},
    # China indices (yfinance-only)
    {"id": "CSI300", "name": "CSI 300", "ticker_yfinance": "000300.SS", "asset_type": "country_index", "country": "CN", "sector": None, "hierarchy_level": 1, "benchmark_id": "ACWI", "currency": "CNY", "liquidity_tier": 1},
    {"id": "SSE_COMP", "name": "SSE Composite", "ticker_yfinance": "000001.SS", "asset_type": "country_index", "country": "CN", "sector": None, "hierarchy_level": 1, "benchmark_id": "ACWI", "currency": "CNY", "liquidity_tier": 1},
    {"id": "SZSE_COMP", "name": "Shenzhen Component", "ticker_yfinance": "399001.SZ", "asset_type": "country_index", "country": "CN", "sector": None, "hierarchy_level": 1, "benchmark_id": "ACWI", "currency": "CNY", "liquidity_tier": 1},
    # Korea indices (yfinance-only)
    {"id": "KS11", "name": "KOSPI", "ticker_yfinance": "^KS11", "asset_type": "country_index", "country": "KR", "sector": None, "hierarchy_level": 1, "benchmark_id": "ACWI", "currency": "KRW", "liquidity_tier": 1},
    {"id": "KS200", "name": "KOSPI 200", "ticker_yfinance": "^KS200", "asset_type": "country_index", "country": "KR", "sector": None, "hierarchy_level": 1, "benchmark_id": "ACWI", "currency": "KRW", "liquidity_tier": 1},
    # India indices (yfinance-only)
    {"id": "NSEI", "name": "NIFTY 50", "ticker_yfinance": "^NSEI", "asset_type": "country_index", "country": "IN", "sector": None, "hierarchy_level": 1, "benchmark_id": "ACWI", "currency": "INR", "liquidity_tier": 1},
    # India sector indices
    {"id": "CNXIT_IN", "name": "NIFTY IT", "ticker_yfinance": "^CNXIT", "asset_type": "sector_index", "country": "IN", "sector": "it", "hierarchy_level": 2, "benchmark_id": "NSEI", "currency": "INR", "liquidity_tier": 1},
    {"id": "NSEBANK_IN", "name": "NIFTY Bank", "ticker_yfinance": "^NSEBANK", "asset_type": "sector_index", "country": "IN", "sector": "bank", "hierarchy_level": 2, "benchmark_id": "NSEI", "currency": "INR", "liquidity_tier": 1},
    {"id": "CNXFIN_IN", "name": "NIFTY Financial Services", "ticker_yfinance": "^CNXFIN", "asset_type": "sector_index", "country": "IN", "sector": "financial_services", "hierarchy_level": 2, "benchmark_id": "NSEI", "currency": "INR", "liquidity_tier": 1},
    {"id": "CNXPHARMA_IN", "name": "NIFTY Pharma", "ticker_yfinance": "^CNXPHARMA", "asset_type": "sector_index", "country": "IN", "sector": "pharma", "hierarchy_level": 2, "benchmark_id": "NSEI", "currency": "INR", "liquidity_tier": 1},
    {"id": "CNXAUTO_IN", "name": "NIFTY Auto", "ticker_yfinance": "^CNXAUTO", "asset_type": "sector_index", "country": "IN", "sector": "auto", "hierarchy_level": 2, "benchmark_id": "NSEI", "currency": "INR", "liquidity_tier": 1},
    {"id": "CNXFMCG_IN", "name": "NIFTY FMCG", "ticker_yfinance": "^CNXFMCG", "asset_type": "sector_index", "country": "IN", "sector": "fmcg", "hierarchy_level": 2, "benchmark_id": "NSEI", "currency": "INR", "liquidity_tier": 1},
    {"id": "CNXMETAL_IN", "name": "NIFTY Metal", "ticker_yfinance": "^CNXMETAL", "asset_type": "sector_index", "country": "IN", "sector": "metal", "hierarchy_level": 2, "benchmark_id": "NSEI", "currency": "INR", "liquidity_tier": 1},
    {"id": "CNXREALTY_IN", "name": "NIFTY Realty", "ticker_yfinance": "^CNXREALTY", "asset_type": "sector_index", "country": "IN", "sector": "realty", "hierarchy_level": 2, "benchmark_id": "NSEI", "currency": "INR", "liquidity_tier": 1},
    {"id": "CNXENERGY_IN", "name": "NIFTY Energy", "ticker_yfinance": "^CNXENERGY", "asset_type": "sector_index", "country": "IN", "sector": "energy", "hierarchy_level": 2, "benchmark_id": "NSEI", "currency": "INR", "liquidity_tier": 1},
    {"id": "CNXINFRA_IN", "name": "NIFTY Infrastructure", "ticker_yfinance": "^CNXINFRA", "asset_type": "sector_index", "country": "IN", "sector": "infrastructure", "hierarchy_level": 2, "benchmark_id": "NSEI", "currency": "INR", "liquidity_tier": 1},
    {"id": "CNXPSUBANK_IN", "name": "NIFTY PSU Bank", "ticker_yfinance": "^CNXPSUBANK", "asset_type": "sector_index", "country": "IN", "sector": "psu_bank", "hierarchy_level": 2, "benchmark_id": "NSEI", "currency": "INR", "liquidity_tier": 1},
    # HK sub-indices (yfinance-only)
    {"id": "HSTECH_HK", "name": "Hang Seng Tech Index", "ticker_yfinance": "^HSTECH", "asset_type": "sector_index", "country": "HK", "sector": "technology", "hierarchy_level": 2, "benchmark_id": "HSI", "currency": "HKD", "liquidity_tier": 1},
    {"id": "HSFI_HK", "name": "Hang Seng Finance Index", "ticker_yfinance": "^HSFI", "asset_type": "sector_index", "country": "HK", "sector": "finance", "hierarchy_level": 2, "benchmark_id": "HSI", "currency": "HKD", "liquidity_tier": 1},
    {"id": "HSPI_HK", "name": "Hang Seng Properties Index", "ticker_yfinance": "^HSPI", "asset_type": "sector_index", "country": "HK", "sector": "properties", "hierarchy_level": 2, "benchmark_id": "HSI", "currency": "HKD", "liquidity_tier": 1},
    {"id": "HSUI_HK", "name": "Hang Seng Utilities Index", "ticker_yfinance": "^HSUI", "asset_type": "sector_index", "country": "HK", "sector": "utilities", "hierarchy_level": 2, "benchmark_id": "HSI", "currency": "HKD", "liquidity_tier": 1},
    # Taiwan (yfinance-only)
    {"id": "TWII", "name": "TWSE", "ticker_yfinance": "^TWII", "asset_type": "country_index", "country": "TW", "sector": None, "hierarchy_level": 1, "benchmark_id": "ACWI", "currency": "TWD", "liquidity_tier": 1},
    {"id": "0050_TW", "name": "Yuanta/P-shares Taiwan Top 50 ETF", "ticker_yfinance": "0050.TW", "asset_type": "sector_etf", "country": "TW", "sector": "large_cap", "hierarchy_level": 2, "benchmark_id": "TWII", "currency": "TWD", "liquidity_tier": 1},
    {"id": "0051_TW", "name": "Yuanta FTSE TWSE Taiwan Mid Cap 100", "ticker_yfinance": "0051.TW", "asset_type": "sector_etf", "country": "TW", "sector": "mid_cap", "hierarchy_level": 2, "benchmark_id": "TWII", "currency": "TWD", "liquidity_tier": 2},
    # Australia (yfinance-only)
    {"id": "AXJO", "name": "ASX 200", "ticker_yfinance": "^AXJO", "asset_type": "country_index", "country": "AU", "sector": None, "hierarchy_level": 1, "benchmark_id": "ACWI", "currency": "AUD", "liquidity_tier": 1},
    {"id": "VAS_AU", "name": "Vanguard Australian Shares ETF", "ticker_yfinance": "VAS.AX", "asset_type": "sector_etf", "country": "AU", "sector": "broad_market", "hierarchy_level": 2, "benchmark_id": "AXJO", "currency": "AUD", "liquidity_tier": 1},
    {"id": "MVB_AU", "name": "VanEck Australian Banks ETF", "ticker_yfinance": "MVB.AX", "asset_type": "sector_etf", "country": "AU", "sector": "banks", "hierarchy_level": 2, "benchmark_id": "AXJO", "currency": "AUD", "liquidity_tier": 2},
    {"id": "OZR_AU", "name": "SPDR S&P/ASX 200 Resources ETF", "ticker_yfinance": "OZR.AX", "asset_type": "sector_etf", "country": "AU", "sector": "resources", "hierarchy_level": 2, "benchmark_id": "AXJO", "currency": "AUD", "liquidity_tier": 2},
    # Brazil (yfinance-only)
    {"id": "BVSP", "name": "IBOVESPA", "ticker_yfinance": "^BVSP", "asset_type": "country_index", "country": "BR", "sector": None, "hierarchy_level": 1, "benchmark_id": "ACWI", "currency": "BRL", "liquidity_tier": 1},
    {"id": "BOVA11_BR", "name": "iShares Ibovespa ETF", "ticker_yfinance": "BOVA11.SA", "asset_type": "sector_etf", "country": "BR", "sector": "broad_market", "hierarchy_level": 2, "benchmark_id": "BVSP", "currency": "BRL", "liquidity_tier": 1},
    {"id": "FIND11_BR", "name": "iShares BM&F Financials ETF", "ticker_yfinance": "FIND11.SA", "asset_type": "sector_etf", "country": "BR", "sector": "financials", "hierarchy_level": 2, "benchmark_id": "BVSP", "currency": "BRL", "liquidity_tier": 2},
    {"id": "MATB11_BR", "name": "iShares BM&F Materials ETF", "ticker_yfinance": "MATB11.SA", "asset_type": "sector_etf", "country": "BR", "sector": "materials", "hierarchy_level": 2, "benchmark_id": "BVSP", "currency": "BRL", "liquidity_tier": 2},
    {"id": "UTIL11_BR", "name": "iShares BM&F Utilities ETF", "ticker_yfinance": "UTIL11.SA", "asset_type": "sector_etf", "country": "BR", "sector": "utilities", "hierarchy_level": 2, "benchmark_id": "BVSP", "currency": "BRL", "liquidity_tier": 2},
    # Canada (yfinance-only)
    {"id": "GSPTSE", "name": "TSX Composite", "ticker_yfinance": "^GSPTSE", "asset_type": "country_index", "country": "CA", "sector": None, "hierarchy_level": 1, "benchmark_id": "ACWI", "currency": "CAD", "liquidity_tier": 1},
    {"id": "XIU_CA", "name": "iShares S&P/TSX 60 Index ETF", "ticker_yfinance": "XIU.TO", "asset_type": "sector_etf", "country": "CA", "sector": "large_cap", "hierarchy_level": 2, "benchmark_id": "GSPTSE", "currency": "CAD", "liquidity_tier": 1},
    {"id": "XFN_CA", "name": "iShares S&P/TSX Capped Financials ETF", "ticker_yfinance": "XFN.TO", "asset_type": "sector_etf", "country": "CA", "sector": "financials", "hierarchy_level": 2, "benchmark_id": "GSPTSE", "currency": "CAD", "liquidity_tier": 1},
    {"id": "XIT_CA", "name": "iShares S&P/TSX Capped IT ETF", "ticker_yfinance": "XIT.TO", "asset_type": "sector_etf", "country": "CA", "sector": "technology", "hierarchy_level": 2, "benchmark_id": "GSPTSE", "currency": "CAD", "liquidity_tier": 2},
    {"id": "XEG_CA", "name": "iShares S&P/TSX Capped Energy ETF", "ticker_yfinance": "XEG.TO", "asset_type": "sector_etf", "country": "CA", "sector": "energy", "hierarchy_level": 2, "benchmark_id": "GSPTSE", "currency": "CAD", "liquidity_tier": 1},
    {"id": "XMA_CA", "name": "iShares S&P/TSX Capped Materials ETF", "ticker_yfinance": "XMA.TO", "asset_type": "sector_etf", "country": "CA", "sector": "materials", "hierarchy_level": 2, "benchmark_id": "GSPTSE", "currency": "CAD", "liquidity_tier": 1},
    {"id": "XHC_CA", "name": "iShares S&P/TSX Capped Healthcare ETF", "ticker_yfinance": "XHC.TO", "asset_type": "sector_etf", "country": "CA", "sector": "healthcare", "hierarchy_level": 2, "benchmark_id": "GSPTSE", "currency": "CAD", "liquidity_tier": 2},
    {"id": "XIN_CA", "name": "iShares S&P/TSX Capped Industrials ETF", "ticker_yfinance": "XIN.TO", "asset_type": "sector_etf", "country": "CA", "sector": "industrials", "hierarchy_level": 2, "benchmark_id": "GSPTSE", "currency": "CAD", "liquidity_tier": 2},
    {"id": "XRE_CA", "name": "iShares S&P/TSX Capped REIT ETF", "ticker_yfinance": "XRE.TO", "asset_type": "sector_etf", "country": "CA", "sector": "real_estate", "hierarchy_level": 2, "benchmark_id": "GSPTSE", "currency": "CAD", "liquidity_tier": 2},
    {"id": "XUT_CA", "name": "iShares S&P/TSX Capped Utilities ETF", "ticker_yfinance": "XUT.TO", "asset_type": "sector_etf", "country": "CA", "sector": "utilities", "hierarchy_level": 2, "benchmark_id": "GSPTSE", "currency": "CAD", "liquidity_tier": 2},
    {"id": "XST_CA", "name": "iShares S&P/TSX Capped Consumer Staples", "ticker_yfinance": "XST.TO", "asset_type": "sector_etf", "country": "CA", "sector": "consumer_staples", "hierarchy_level": 2, "benchmark_id": "GSPTSE", "currency": "CAD", "liquidity_tier": 2},
    # Korea sector ETFs (yfinance)
    {"id": "TIGER_KR", "name": "TIGER 200 IT ETF", "ticker_yfinance": "139260.KS", "asset_type": "sector_etf", "country": "KR", "sector": "technology", "hierarchy_level": 2, "benchmark_id": "KS11", "currency": "KRW", "liquidity_tier": 2},
    {"id": "KODEX_FIN_KR", "name": "KODEX Financials ETF", "ticker_yfinance": "091170.KS", "asset_type": "sector_etf", "country": "KR", "sector": "financials", "hierarchy_level": 2, "benchmark_id": "KS11", "currency": "KRW", "liquidity_tier": 2},
    {"id": "KODEX_HC_KR", "name": "KODEX Healthcare ETF", "ticker_yfinance": "266360.KS", "asset_type": "sector_etf", "country": "KR", "sector": "healthcare", "hierarchy_level": 2, "benchmark_id": "KS11", "currency": "KRW", "liquidity_tier": 2},
    {"id": "KODEX_IND_KR", "name": "KODEX Industrials ETF", "ticker_yfinance": "091160.KS", "asset_type": "sector_etf", "country": "KR", "sector": "industrials", "hierarchy_level": 2, "benchmark_id": "KS11", "currency": "KRW", "liquidity_tier": 2},
    {"id": "KODEX_SEM_KR", "name": "KODEX Semiconductor ETF", "ticker_yfinance": "091180.KS", "asset_type": "sector_etf", "country": "KR", "sector": "semiconductors", "hierarchy_level": 2, "benchmark_id": "KS11", "currency": "KRW", "liquidity_tier": 2},
    {"id": "KODEX_BAT_KR", "name": "KODEX Secondary Battery ETF", "ticker_yfinance": "305720.KS", "asset_type": "sector_etf", "country": "KR", "sector": "battery", "hierarchy_level": 2, "benchmark_id": "KS11", "currency": "KRW", "liquidity_tier": 2},
]


def generate() -> None:
    """Generate the comprehensive instrument_map.json."""
    classifier = ETFClassifier()
    all_entries: list[dict] = []
    seen_ids: set[str] = set()

    def add_entry(entry: dict) -> None:
        eid = entry["id"]
        if eid not in seen_ids:
            all_entries.append(entry)
            seen_ids.add(eid)

    # 1. Stooq indices
    logger.info("Adding %d Stooq indices...", len(KNOWN_INDICES))
    for ticker, info in KNOWN_INDICES.items():
        classification = classifier.classify_index(ticker)
        name = INDEX_NAMES.get(ticker, ticker)
        entry = build_instrument_entry(ticker, name, classification, source="stooq")
        add_entry(entry)

    # 2. All US-listed ETFs from KNOWN_ETFS (Stooq .US suffix)
    logger.info("Adding %d US-listed ETFs...", len(KNOWN_ETFS))
    for base_ticker, info in KNOWN_ETFS.items():
        # ACWI is yfinance-only (already in YFINANCE_INSTRUMENTS)
        if base_ticker == "ACWI":
            continue
        stooq_ticker = f"{base_ticker}.US"
        name = ETF_NAMES.get(base_ticker, f"ETF: {base_ticker}")
        classification = classifier.classify(stooq_ticker, name)
        entry = build_instrument_entry(stooq_ticker, name, classification, source="stooq")
        add_entry(entry)

    # 3. Japan sector ETFs (.JP suffix on Stooq)
    logger.info("Adding %d Japan ETFs...", len(JAPAN_SECTOR_ETFS))
    for etf in JAPAN_SECTOR_ETFS:
        ticker = etf["ticker"]
        entry_id = ticker.replace(".", "_")
        entry = {
            "id": entry_id,
            "name": etf["name"],
            "ticker_stooq": ticker,
            "ticker_yfinance": None,
            "source": "stooq",
            "asset_type": "sector_etf" if etf["sector"] else "country_etf",
            "country": "JP",
            "sector": etf["sector"],
            "hierarchy_level": 2 if etf["sector"] else 1,
            "benchmark_id": "NKX",
            "currency": "JPY",
            "liquidity_tier": 2,
        }
        add_entry(entry)

    # 4. Hong Kong ETFs (.HK suffix on Stooq)
    logger.info("Adding %d HK ETFs...", len(HK_ETFS))
    for etf in HK_ETFS:
        ticker = etf["ticker"]
        entry_id = ticker.replace(".", "_")
        country = etf.get("country", "HK")
        sector = etf.get("sector")
        benchmark = "HSI" if country == "HK" else "CSI300" if country == "CN" else "ACWI"
        entry = {
            "id": entry_id,
            "name": etf["name"],
            "ticker_stooq": ticker,
            "ticker_yfinance": None,
            "source": "stooq",
            "asset_type": "sector_etf" if sector else "country_etf",
            "country": country,
            "sector": sector,
            "hierarchy_level": 2 if sector else 1,
            "benchmark_id": benchmark,
            "currency": "HKD",
            "liquidity_tier": 1 if country == "HK" else 2,
        }
        add_entry(entry)

    # 5. yfinance gap-fill instruments (India, Korea, China, Taiwan, AU, BR, CA)
    logger.info("Adding %d yfinance gap-fill instruments...", len(YFINANCE_INSTRUMENTS))
    for inst in YFINANCE_INSTRUMENTS:
        entry = {
            "id": inst["id"],
            "name": inst["name"],
            "ticker_stooq": None,
            "ticker_yfinance": inst["ticker_yfinance"],
            "source": "yfinance",
            "asset_type": inst["asset_type"],
            "country": inst.get("country"),
            "sector": inst.get("sector"),
            "hierarchy_level": inst["hierarchy_level"],
            "benchmark_id": inst.get("benchmark_id"),
            "currency": inst["currency"],
            "liquidity_tier": inst.get("liquidity_tier", 2),
        }
        add_entry(entry)

    # Sort: benchmarks first, then by hierarchy, country, id
    def sort_key(e: dict) -> tuple:
        type_order = {
            "benchmark": 0,
            "country_index": 1,
            "country_etf": 2,
            "regional_etf": 3,
            "global_sector_etf": 4,
            "sector_index": 5,
            "sector_etf": 6,
            "bond_etf": 7,
            "commodity_etf": 8,
            "etf_unclassified": 9,
        }
        return (
            type_order.get(e.get("asset_type", ""), 99),
            e.get("hierarchy_level", 99),
            e.get("country") or "ZZZ",
            e.get("id", ""),
        )

    all_entries.sort(key=sort_key)

    # Write
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, indent=2, ensure_ascii=False)

    # Stats
    stooq_count = sum(1 for e in all_entries if e["source"] == "stooq")
    yfinance_count = sum(1 for e in all_entries if e["source"] == "yfinance")
    by_type: dict[str, int] = {}
    for e in all_entries:
        t = e.get("asset_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    logger.info("=" * 60)
    logger.info("Generated instrument_map.json: %d total instruments", len(all_entries))
    logger.info("  Stooq: %d | yfinance: %d", stooq_count, yfinance_count)
    logger.info("  By type:")
    for t, c in sorted(by_type.items()):
        logger.info("    %-25s %d", t, c)
    logger.info("  Output: %s", OUTPUT_PATH)
    logger.info("=" * 60)


if __name__ == "__main__":
    generate()
