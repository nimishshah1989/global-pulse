#!/usr/bin/env python3
"""
Tag ETFs in instrument_map.json with sector metadata.

Reads the instrument map, identifies hierarchy_level=2 instruments with
missing sector tags, and applies keyword-based classification from the
instrument name. Also flags potential country tag issues.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

INSTRUMENT_MAP_PATH = Path(__file__).parent.parent / "data" / "instrument_map.json"

# ---------------------------------------------------------------------------
# Keyword rules: list of (compiled_regex, sector_tag)
# Order matters — first match wins. More specific patterns come before general.
# ---------------------------------------------------------------------------

def _build_rules():
    """Build ordered list of (regex, sector) rules."""
    # Each entry: (pattern_string, sector, flags)
    # Patterns are matched against the FULL instrument name (case-insensitive).
    raw_rules = [
        # ===== FIXED INCOME / BOND sub-types (must come before broad bond) =====
        (r'\b(t-?bill|treasury bill|ultra.?short.?gov)', 'treasury_ultrashort'),
        (r'\b(0-1|0-3|1-3|0-2).*(year|yr|mo).*treas', 'treasury_short'),
        (r'\b(treas|govt|government).*(0-1|0-3|1-3|0-2|short)', 'treasury_short'),
        (r'\bshort.*(term|dur).*treas', 'treasury_short'),
        (r'\b(3-7|3-10|5-10|4-8|7-10).*(year|yr).*treas', 'treasury_mid'),
        (r'\b(treas|govt|government).*(3-7|3-10|5-10|4-8|7-10|inter)', 'treasury_mid'),
        (r'\binter.*treas', 'treasury_mid'),
        (r'\b(10-20|10-30|20\+|20-30|25\+|long).*(year|yr|term|dur).*treas', 'treasury_long'),
        (r'\b(treas|govt|government).*(10-20|10-30|20\+|20-30|25\+|long)', 'treasury_long'),
        (r'\blong.*(term|dur).*treas', 'treasury_long'),
        (r'\btreasury.*strip', 'treasury_strips'),
        (r'\btips\b|inflation.*(protect|link|index)|real.?return', 'tips'),
        (r'\bfloating.?rate|float.*rate|senior.?loan|bank.?loan|lever.*loan', 'floating_rate'),
        (r'\bclo\b|collateral.*loan', 'clo'),
        (r'\bmortgage|mbs\b|mort.*back', 'mortgage_backed'),
        (r'\bmuni|municipal', 'municipal'),
        (r'\bhigh.?yield|junk.?bond|fallen.?angel', 'high_yield'),
        (r'\binvest.*grade|ig\b.*corp|corp.*ig\b', 'investment_grade'),
        (r'\bconvert|conversion', 'convertible_bond'),
        (r'\bpref.*stock|prefer', 'preferred_stock'),
        (r'\b(em|emerging).*(bond|debt|sov|fixed)', 'em_bond'),
        (r'\b(bond|debt|sov|fixed).*(em|emerging)', 'em_bond'),
        (r'\bint.*l.*bond|global.*bond|world.*bond|foreign.*bond', 'intl_bond'),
        (r'\bint.*l.*treas|global.*treas|foreign.*treas', 'intl_treasury'),
        (r'\b(short|ultra).*(term|dur).*corp', 'short_corp'),
        (r'\bcorp.*(short|ultra)', 'short_corp'),
        (r'\binter.*(term|dur)?.*corp', 'intermediate_corp'),
        (r'\bcorp.*inter', 'intermediate_corp'),
        (r'\blong.*(term|dur).*corp', 'long_corp'),
        (r'\bcorp.*long', 'long_corp'),
        (r'\bcorporate.?bond|corp.?bond', 'corporate_bond'),
        (r'\baggregate|agg\b.*bond|total.*bond|core.*bond|broad.*bond|u\.?s\.? bond|us bond', 'aggregate_bond'),
        (r'\btotal.*return.*bond|diversif.*bond|multi.*sector.*bond', 'aggregate_bond'),
        (r'\btarget.*date|maturity.*\d{4}|bull.*\d{4}|term\s*\d{4}', 'target_date_bond'),
        (r'\byield|income|interest.?rate', 'fixed_income_other'),
        # Catch remaining bonds
        (r'\bbond|fixed.?income|debt|treasury|govt.*sec|government.*sec', 'aggregate_bond'),

        # ===== CRYPTO =====
        (r'\bbitcoin|btc\b', 'bitcoin'),
        (r'\bethe?r(eum)?|eth\b', 'ethereum'),
        (r'\bsolana|sol\b(?!.*ar)', 'solana'),
        (r'\bdogecoin|doge\b', 'dogecoin'),
        (r'\bxrp\b', 'xrp'),
        (r'\bsui\b', 'sui'),
        (r'\bhbar\b', 'hbar'),
        (r'\bchainlink\b', 'chainlink'),
        (r'\baltcoin', 'crypto'),
        (r'\bcrypto|blockchain|digital.?asset|defi\b|web3\b|onchain', 'crypto'),

        # ===== COMMODITIES (specific before broad) =====
        (r'\bgold\b.*miner.*junior|junior.*gold.*miner', 'gold_miners_jr'),
        (r'\bgold\b.*miner|miner.*gold', 'gold_miners'),
        (r'\bsilver.*miner|miner.*silver', 'silver_miners'),
        (r'\bcopper.*miner|miner.*copper', 'copper_miners'),
        (r'\buranium|nuclear\b(?!.*weapon)', 'uranium'),
        (r'\blithium|battery.*metal', 'lithium_battery'),
        (r'\brare.?earth|critical.*mineral|strategic.*metal', 'rare_earth'),
        (r'\bgold\b(?!.*man)', 'gold'),
        (r'\bsilver\b', 'silver'),
        (r'\bplatinum\b', 'platinum'),
        (r'\bpalladium\b', 'palladium'),
        (r'\bcrude|wti\b|brent\b|\boil\b(?!.*service)(?!.*explor)', 'crude_oil'),
        (r'\bnatural.?gas|natgas|henry.?hub', 'natural_gas'),
        (r'\bgasoline|rbob\b', 'gasoline'),
        (r'\bwheat\b', 'wheat'),
        (r'\bcorn\b', 'corn'),
        (r'\bsoy\b|soybean', 'soybeans'),
        (r'\bsugar\b', 'sugar'),
        (r'\bcoffee\b', 'coffee'),
        (r'\bcocoa\b', 'cocoa'),
        (r'\bcotton\b', 'cotton'),
        (r'\bcattle\b|livestock', 'livestock'),
        (r'\bagri|farm|crop', 'agriculture'),
        (r'\bcarbon|emission|allowance', 'carbon'),
        (r'\btimber|wood|lumber', 'timber'),
        (r'\bwater\b(?!.*fall)', 'water'),
        (r'\bcommod|raw.?material|natural.?resource|hard.?asset', 'commodities_broad'),
        (r'\bmetal(?!.*lurg)', 'metals_broad'),
        (r'\bbase.?metal', 'metals_broad'),
        (r'\btanker|shipping|freight', 'shipping'),

        # ===== SECTOR-SPECIFIC (specific sub-sectors first) =====
        # Tech sub-sectors
        (r'\bsemiconductor|chip\b|soxx\b|smh\b', 'semiconductors'),
        (r'\bcyber\b|cybersecur|network.?secur|information.?secur', 'cybersecurity'),
        (r'\bcloud\b|saas\b|software.?as.*service', 'cloud_computing'),
        (r'\b(artificial|a\.?i\.?).?intell|machine.?learn|deep.?learn|\bai\b.*(?:tech|etf|fund|index)', 'artificial_intelligence'),
        (r'\brobot|automat(?!.*otive)|autonomous.*tech', 'robotics_ai'),
        (r'\bfintech|financial.*tech|digital.*pay|payment.*tech', 'fintech'),
        (r'\b3d.?print|addit.*manufactur', '3d_printing'),
        (r'\bvideo.?game|gaming|esport|e-sport', 'gaming'),
        (r'\bsocial.?media|digital.?media|streaming', 'digital_media'),
        (r'\binternet|online|e-?commerce|digital.*comm', 'internet'),
        (r'\bdata.?center|server\b', 'data_centers'),
        (r'\bspace\b(?!.*real)|orbit|satellite|aerosp.*space', 'space'),
        (r'\btech(nology)?|info.*tech|software|hardware|comput(?!.*cloud)', 'technology'),

        # Healthcare sub-sectors
        (r'\bgenomic|crispr|gene.*edit|dna\b', 'genomics'),
        (r'\bbiotech|biotechnol', 'biotech'),
        (r'\bpharma(?!.*ceut)|drug|therapeut', 'pharma'),
        (r'\bpharmaceut', 'pharma'),
        (r'\bmedical.*device|med.*tech|med.?device|health.*equip', 'medical_devices'),
        (r'\bhealth\s*care|health|medical|biomed', 'healthcare'),

        # Energy sub-sectors
        (r'\bsolar\b', 'solar'),
        (r'\bwind\b(?!.*mill).*(?:energ|power|turbin)', 'wind_energy'),
        (r'\bclean.*energ|renew.*energ|alt.*energ|green.*energ|transition.*energ', 'clean_energy'),
        (r'\boil.*service|oilfield|drilling', 'oil_services'),
        (r'\boil.*gas.*expl|explor.*prod|upstream|e&p\b', 'oil_gas_exploration'),
        (r'\bmlp\b|master.*limit.*partner|midstream|pipeline', 'mlp_midstream'),
        (r'\benergy|power(?!.*shares)(?!.*buffer)', 'energy'),

        # Financials sub-sectors
        (r'\bregional.*bank|community.*bank|small.*bank', 'regional_banks'),
        (r'\bbank(?!.*rupt)|banking', 'banks'),
        (r'\binsurance|insurer|underwriter', 'insurance'),
        (r'\breal\s*estate|reit|property|propert|housing|mortgage(?!.*back)', 'real_estate'),
        (r'\bfinancial|financ(?!.*tech)', 'financials'),

        # Industrials sub-sectors
        (r'\baero.*def|defense|defen[cs]e|military|weapon|arm[eo]', 'aerospace_defense'),
        (r'\baerospace(?!.*def)', 'aerospace_defense'),
        (r'\bhome.?build|residential.*construct|housing.*construct', 'homebuilders'),
        (r'\bairline|aviation|air.*travel', 'airlines'),
        (r'\btransport(?!.*equip)|logistic|trucking|freight(?!.*rate)', 'transportation'),
        (r'\binfra(?:struct)?|construct(?!.*home)', 'infrastructure'),
        (r'\bindustr', 'industrials'),

        # Consumer sub-sectors
        (r'\bcannabis|marijuana|weed\b', 'cannabis'),
        (r'\bluxury\b|prestige|premium.*brand', 'luxury'),
        (r'\bretail|consumer.*discr|discretion', 'consumer_discretionary'),
        (r'\bstaple|consumer.*staple|food.*bev|household.*prod', 'consumer_staples'),
        (r'\bconsumer(?!.*discr)(?!.*stapl)', 'consumer_discretionary'),

        # Communication
        (r'\btelecom|communicat', 'communication'),
        (r'\bmedia(?!.*social)(?!.*stream)', 'communication'),

        # Materials
        (r'\bmaterial|basic.*material|chemical|mining(?!.*gold)(?!.*silver)(?!.*copper)(?!.*uran)', 'materials'),
        (r'\bsteel|iron\b', 'iron_steel'),

        # Utilities
        (r'\butilit', 'utilities'),

        # ===== LEVERAGED SINGLE-STOCK ETFs =====
        # Match patterns like "2X Long NVDA", "Bull 2X ETF", "Bear 1X", etc. with specific tickers
        (r'\b(long|bull|short|bear|inverse).*\b(NVDA|NVIDIA)\b|\b(NVDA|NVIDIA)\b.*(long|bull|short|bear|inverse)', 'leveraged_single_stock'),
        (r'\b(long|bull|short|bear|inverse).*\b(TSLA|Tesla)\b|\b(TSLA|Tesla)\b.*(long|bull|short|bear|inverse)', 'leveraged_single_stock'),
        (r'\b(long|bull|short|bear|inverse).*\b(META|GOOGL|AMZN|AAPL|MSFT|NFLX)\b', 'leveraged_single_stock'),
        (r'\b(long|bull|short|bear|inverse).*\b(AVGO|AMD|COIN|HOOD|SHOP|CRM|PANW)\b', 'leveraged_single_stock'),
        (r'\b(long|bull|short|bear|inverse).*\b(SMCI|BABA|PDD|PYPL|UBER|QCOM)\b', 'leveraged_single_stock'),
        (r'\b(long|bull|short|bear|inverse).*\b(LLY|NVO|INTC|BA|XOM|LMT|BRKB|TSM)\b', 'leveraged_single_stock'),
        (r'\b(long|bull|short|bear|inverse).*\b(CRWD|NET|SNOW|RBLX|GME|RDDT|VRT|VST)\b', 'leveraged_single_stock'),
        (r'\b(long|bull|short|bear|inverse).*\b(MSTR|SMR|SOFI|SOUN|RGTI|QUBT|QBTS|OKLO)\b', 'leveraged_single_stock'),
        (r'\b(long|bull|short|bear|inverse).*\b(JOBY|ENPH|UPST|OPEN|SRPT|NVTS|NNE|CORZ)\b', 'leveraged_single_stock'),
        (r'\b(long|bull|short|bear|inverse).*\b(CLSK|CEG|SNPS|LRCX|MDB|TEM|WULF|VOYG)\b', 'leveraged_single_stock'),
        (r'\b(long|bull|short|bear|inverse).*\b(ASTS|ALAB|LCID|CMG|OKTA|FLY|TTD|CRDO)\b', 'leveraged_single_stock'),
        (r'\b(long|bull|short|bear|inverse).*\b(NBIS|AVAV|LMND|KTOS|NEM|TER|FIG|FUTU)\b', 'leveraged_single_stock'),
        (r'\b(long|bull|short|bear|inverse).*\b(BLSH|BMNR|CRCL|CRWV|GLXY|BU|BE)\b', 'leveraged_single_stock'),
        # Generic leveraged patterns: "2x Long ... Daily ETF", "GraniteShares 2x", "Leverage Shares 2X", "T-REX 2X"
        (r'\b(GraniteShares|Leverage\s*Shares|T-?REX|Tradr|Defiance Daily Target)\b.*\b(2[xX]|1\.?5[xX]|3[xX])\b', 'leveraged_single_stock'),
        (r'\b(2[xX]|1\.?5[xX]|3[xX])\b.*\b(Long|Short|Bull|Bear|Inverse)\b.*\bDaily\b', 'leveraged_single_stock'),
        (r'\bRoundhill\b.*\bWeeklyPay\b', 'covered_call'),
        (r'\bDirexion Daily\b.*\b(Bull|Bear)\b.*\b[12][xX]\b', 'leveraged_single_stock'),

        # ===== STRUCTURED OUTCOME / BUFFER ETFs =====
        (r'\bstructured.*outcome|structured.*alt.*protect', 'buffer_strategy'),
        (r'\bpacer.*swan.*sos|swan.*sos', 'buffer_strategy'),
        (r'\btarget.*range', 'buffer_strategy'),

        # ===== MANAGED FUTURES =====
        (r'\bmanaged.*futur|futures.*strateg|trend.*follow|systematic.*trend|cta\b', 'managed_futures'),

        # ===== VIX / VOLATILITY =====
        (r'\bvix\b|volatility.*future|short.?term.*future.*etn', 'volatility'),

        # ===== LEVERAGED INDEX ETFs =====
        (r'\bultra.*pro.*short|ultrapro.*short', 'leveraged_index_inverse'),
        (r'\bultra.*pro|ultrapro', 'leveraged_index'),
        (r'\bultra.*short|ultrashort', 'leveraged_index_inverse'),
        (r'\bultra\b(?!.*short).*(?:dow|qqq|s&p|russell|euro|msci)', 'leveraged_index'),
        (r'\bshort\b.*\b(qqq|dow|spy|s&p)', 'leveraged_index_inverse'),

        # ===== CURRENCY =====
        (r'\bcurrency\s*share|currencyshare|currency.*trust|fx\b.*trust|dollar.*trust|yen.*trust|euro.*trust|pound.*trust|franc.*trust|bullish.*fund.*dollar|dollar.*bullish', 'currency'),

        # ===== COUNTRY-SPECIFIC (for country_etfs without sector) =====
        (r'\bchina|chinese|csi\s*300|hang\s*seng|chinext', 'country_equity'),
        (r'\bjapan|japanese|nikkei|jpx\b', 'country_equity'),
        (r'\bindia|indian|nifty', 'country_equity'),
        (r'\bkorea|korean|kospi', 'country_equity'),
        (r'\bbrazil|brazilian|ibov', 'country_equity'),
        (r'\bcanada|canadian|tsx\b', 'country_equity'),
        (r'\bgermany|german|dax\b', 'country_equity'),
        (r'\bunited\s*kingdom|british|uk\b|ftse\b', 'country_equity'),
        (r'\bswiss|switzerland', 'country_equity'),
        (r'\baustralia|australian|asx\b', 'country_equity'),
        (r'\biceland', 'country_equity'),

        # ===== SINGLE-STOCK ADR-HEDGED =====
        (r'\bADRhedged\b|adr.*hedg', 'adr_hedged'),

        # ===== THEMATIC =====
        (r'\binnovat|disrupt', 'innovation'),
        (r'\besg\b|sustain|responsible|impact.*invest|socially.*resp|sri\b|green\b', 'esg'),
        (r'\bmetaverse|virtual.*reality|augmented.*reality|xr\b', 'metaverse'),
        (r'\belectric.*vehicle|ev\b(?!.*ent)|autonomous.*driv|self.*driv', 'electric_vehicles'),
        (r'\binfosec|privacy|data.*protect', 'cybersecurity'),
        (r'\bfood.*security|agri.*tech|precision.*agri', 'agritech'),
        (r'\baging|longev|senior.*care', 'aging_demographics'),
        (r'\bmillennial|gen.*z', 'demographic'),

        # ===== STYLE / STRATEGY =====
        (r'\bdividend|distr.*yield|high.*div|div.*grow|div.*income|div.*achiev|div.*aristocr', 'dividends'),
        (r'\bmomentum\b', 'momentum'),
        (r'\blow.*vol|min.*vol|low.*beta|managed.*vol', 'low_volatility'),
        (r'\bbuy.?write|covered.*call|option.*income|put.*write', 'covered_call'),
        (r'\bbuffer|defined.*outcome|target.*outcome|floor\b', 'buffer_strategy'),
        (r'\bmerger|arbitrage|event.*driven|risk.*arb', 'merger_arbitrage'),
        (r'\bhedge|long.?short|market.*neutral|absolute.*return|alternative', 'alternative_strategy'),
        (r'\bquality\b', 'quality'),
        (r'\bvalue\b(?!.*chain)', 'value'),
        (r'\bgrowth\b', 'growth'),
        (r'\bcore\b(?!.*bond)', 'core'),
        (r'\bequal.*weight|eq.*wt', 'equal_weight'),
        (r'\bmicro.?cap', 'micro_cap'),
        (r'\bnano.?cap', 'nano_cap'),
        (r'\bsmall.?cap|sm.*cap|russell.*2000|small.*co', 'small_cap'),
        (r'\bmid.?cap|midcap|russell.*mid|s&p.*mid|s&p.*400', 'mid_cap'),
        (r'\blarge.?cap|largecap|mega.?cap|s&p.*500|russell.*1000', 'large_cap'),
        (r'\b(total|all|entire|whole).*(?:market|stock|equit)', 'broad_market'),
        (r'\bbroad|diversif.*equit|all.?cap', 'broad_market'),

        # ===== CATCH-ALL for remaining regional/country ETFs =====
        (r'\b(europe|emea|asia|latin|global|world|develop|frontier|emerg|intern)', 'broad_market'),

        # Tactical / rotation / allocation
        (r'\btactical|rotation|allocat|nav\b.*etf|navigator|dynamic', 'tactical_allocation'),
        (r'\bfocused|select|concentrated|opportunit|unconstrain|flex\b', 'active_equity'),
        (r'\bcash.*cow|free.*cash|profitab|cash.*flow', 'quality'),
        (r'\bmoat\b|wide.*moat|competitive.*adv', 'quality'),
        (r'\bfactor\b|multi.*factor|smart.*beta', 'multi_factor'),
        (r'\bpet\b.*care|animal', 'thematic'),
        (r'\bpsychedelics', 'thematic'),
        (r'\bjewish|faith|relig|inspir', 'thematic'),
        (r'\bwomen|gender|female', 'thematic'),
        (r'\bvice\b|sin\b', 'thematic'),
        (r'\bpatriot|republic|democrat|subversive', 'thematic'),
        (r'\btexas|state\b.*equity', 'thematic'),
        (r'\bprivate.*credit|private.*equity|pe\/vc|crossover', 'private_markets'),
        (r'\bmoney.*market|cash.*manage', 'money_market'),
        (r'\bsofr\b|overnight.*rate', 'money_market'),
        (r'\bclosed.?end|cef\b', 'closed_end_funds'),
        (r'\binflation\b|real.*asset', 'inflation_hedge'),
        (r'\bexport|trade.*leader', 'thematic'),
        (r'\bsentiment|social\b.*(?:50|media)|meme\b', 'thematic'),

        # iBonds / target maturity corporate
        (r'\bibonds|term\s*corporate', 'target_date_bond'),
        (r'\bcorporate.*ladder', 'target_date_bond'),

        # Short maturity / low duration bonds
        (r'\bshort.*matur|low.*dur|ultra.*short|short.*dur', 'short_duration_bond'),
        (r'\bshort\s*term\b.*(?:etf|fund|bond)', 'short_duration_bond'),
        (r'\blong.*dur', 'long_duration_bond'),

        # Credit / structured products
        (r'\bcredit\b(?!.*card)', 'credit'),
        (r'\bstructured.*product', 'structured_products'),
        (r'\bdeflation', 'fixed_income_other'),
        (r'\bbox\b.*etf', 'fixed_income_other'),
        (r'\btotal.*return\b(?!.*guard)', 'aggregate_bond'),
        (r'\bballast|conservative\b', 'conservative'),

        # Travel
        (r'\btravel\b|microsectors.*travel', 'travel'),

        # Environmental
        (r'\benvironmental|climate|etho\b|planet|clean(?!.*energ)', 'esg'),

        # Trend following
        (r'\btrend\b|pure.*trend|full.*cycle', 'managed_futures'),

        # Specific named funds/brands
        (r'\bmagellan\b', 'active_equity'),
        (r'\b(barron|morningstar)\b', 'broad_equity'),
        (r'\bstrive\b.*500|gotham.*500|enhanced.*500|transform.*500', 'broad_equity'),
        (r'\bendowment', 'multi_asset'),
        (r'\brisk.*parity|multi.*asset', 'multi_asset'),
        (r'\bmonopol|oligopol', 'thematic'),
        (r'\bknowledge|leader|alpha\b(?!.*dex)', 'active_equity'),
        (r'\bshort\b.*(?:strat|etf)', 'short_equity'),
        (r'\bsynthequity|synth\b', 'active_equity'),
        (r'\bwealth.*shield|guard\b|tail.*risk|protect', 'hedged_equity'),
        (r'\boption.*strat|option.*income', 'options_strategy'),
        (r'\bimprover|rating|analyst', 'active_equity'),
        (r'\bappreciation|grower|compounder', 'quality'),
        (r'\bextended.*market', 'broad_equity'),
        (r'\b(eurozone|europe)\b', 'broad_market'),
        (r'\bdeglobal', 'thematic'),
        (r'\bnexgen|next\s*gen', 'thematic'),
        (r'\bdistribution|weekly.*pay', 'covered_call'),

        # Very generic equity catch-alls
        (r'\bequity|stock|u\.?s\.?\s|us\s|america|dow\b|djia|spy\b|qqq\b|nasdaq|s&p', 'broad_equity'),
        (r'\bactive\b|managed\b', 'active_equity'),
        (r'\bfund\b.*fund|fof\b', 'fund_of_funds'),

        # TSLA-related
        (r'\btsla\b|tesla', 'leveraged_single_stock'),
        # NVDA + AMD combos
        (r'\bnvda\b.*\bamd\b|\bamd\b.*\bnvda\b', 'semiconductors'),

        # Specific branded funds with no sector keyword — map by known name
        (r'\bsarmaya\b.*thematic|thematic\b', 'thematic'),
        (r'\bsmart\s*sector|sector\b(?!.*matrix)', 'tactical_allocation'),
        (r'\bpremia|systematic', 'multi_factor'),
        (r'\bmulti.*strategy|strategy.*track', 'alternative_strategy'),
        (r'\brising.*rate', 'inflation_hedge'),
        (r'\bdeletion|research.*affil', 'active_equity'),
        (r'\blandmark|horizon\b', 'fixed_income_other'),

        # Absolute last resort: anything remaining gets tagged by asset_type
        # (handled in main() fallback, not here)

        # Very last resort for plain "ETFs" / "Fund" with no sector signal
        (r'\bindex\b|idx\b|s&p\b|msci\b|ftse\b|stoxx\b|russell\b', 'broad_market'),
        # Generic ETF/Fund fallback
        (r'\betf\b|\bfund\b', 'active_equity'),
    ]

    compiled = []
    for pattern, sector in raw_rules:
        compiled.append((re.compile(pattern, re.IGNORECASE), sector))
    return compiled


RULES = _build_rules()


def classify_name(name: str) -> str | None:
    """Return a sector tag for the given instrument name, or None if no match."""
    for regex, sector in RULES:
        if regex.search(name):
            return sector
    return None


# ---------------------------------------------------------------------------
# Country-tag auditing
# ---------------------------------------------------------------------------

# ETFs that say "ex-China" or "ex China" or "Beyond China" should NOT be tagged CN
COUNTRY_EXCLUSION_PATTERNS = [
    (re.compile(r'\bex[\s-]china|beyond\s*china|ex[\s-]cn\b', re.IGNORECASE), 'CN'),
    (re.compile(r'\bex[\s-]japan|beyond\s*japan|ex[\s-]jp\b', re.IGNORECASE), 'JP'),
    (re.compile(r'\bex[\s-]us\b|ex[\s-]u\.s\.|beyond\s*us\b', re.IGNORECASE), 'US'),
    (re.compile(r'\bex[\s-]emerg|ex[\s-]em\b', re.IGNORECASE), None),  # generic flag
]


def audit_country_tag(instrument: dict) -> str | None:
    """Return a warning string if the country tag looks wrong, else None."""
    name = instrument.get('name', '')
    country = instrument.get('country')
    if not country:
        return None

    for regex, flagged_country in COUNTRY_EXCLUSION_PATTERNS:
        if regex.search(name):
            if flagged_country and country == flagged_country:
                return (
                    f"Possibly wrong country={country}: name '{name}' "
                    f"suggests 'ex-{country}' exposure, not {country} itself"
                )
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    with open(INSTRUMENT_MAP_PATH) as f:
        data = json.load(f)

    print(f"Loaded {len(data)} instruments from {INSTRUMENT_MAP_PATH}")

    level2 = [i for i in data if i.get('hierarchy_level') == 2]
    already_tagged = [i for i in level2 if i.get('sector')]
    untagged = [i for i in level2 if not i.get('sector')]

    print(f"\nLevel 2 instruments: {len(level2)}")
    print(f"  Already tagged:   {len(already_tagged)}")
    print(f"  Untagged:         {len(untagged)}")

    # Build a lookup by id for mutation
    id_to_idx = {inst['id']: idx for idx, inst in enumerate(data)}

    tagged_count = 0
    still_untagged = []
    sector_assignments = Counter()

    for inst in untagged:
        sector = classify_name(inst['name'])
        if sector:
            data[id_to_idx[inst['id']]]['sector'] = sector
            tagged_count += 1
            sector_assignments[sector] += 1
        else:
            still_untagged.append(inst)

    print(f"\n--- RESULTS ---")
    print(f"Newly tagged:       {tagged_count}")
    print(f"Still untagged:     {len(still_untagged)}")
    print(f"Total now tagged:   {len(already_tagged) + tagged_count} / {len(level2)}")

    print(f"\nSector assignment breakdown (new tags):")
    for sector, count in sorted(sector_assignments.items(), key=lambda x: -x[1]):
        print(f"  {sector:30s}: {count}")

    if still_untagged:
        print(f"\n--- STILL UNTAGGED ({len(still_untagged)}) ---")
        for inst in still_untagged[:50]:
            print(f"  {inst['id']:30s} | {inst['name']:65s} | type={inst['asset_type']}")
        if len(still_untagged) > 50:
            print(f"  ... and {len(still_untagged) - 50} more")

    # Country tag audit
    print(f"\n--- COUNTRY TAG AUDIT ---")
    country_issues = []
    for inst in level2:
        warning = audit_country_tag(inst)
        if warning:
            country_issues.append((inst['id'], warning))

    if country_issues:
        print(f"Found {len(country_issues)} potential country tag issues:")
        for iid, warning in country_issues:
            print(f"  {iid}: {warning}")
    else:
        print("No country tag issues found.")

    # Write updated file
    with open(INSTRUMENT_MAP_PATH, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\nUpdated file written to {INSTRUMENT_MAP_PATH}")


if __name__ == '__main__':
    main()
