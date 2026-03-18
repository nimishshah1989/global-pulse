import type { RankingItem } from '@/types/rs'

export const COUNTRY_FLAGS: Record<string, string> = {
  US: '\uD83C\uDDFA\uD83C\uDDF8',
  UK: '\uD83C\uDDEC\uD83C\uDDE7',
  GB: '\uD83C\uDDEC\uD83C\uDDE7',
  DE: '\uD83C\uDDE9\uD83C\uDDEA',
  FR: '\uD83C\uDDEB\uD83C\uDDF7',
  JP: '\uD83C\uDDEF\uD83C\uDDF5',
  HK: '\uD83C\uDDED\uD83C\uDDF0',
  CN: '\uD83C\uDDE8\uD83C\uDDF3',
  KR: '\uD83C\uDDF0\uD83C\uDDF7',
  IN: '\uD83C\uDDEE\uD83C\uDDF3',
  TW: '\uD83C\uDDF9\uD83C\uDDFC',
  AU: '\uD83C\uDDE6\uD83C\uDDFA',
  BR: '\uD83C\uDDE7\uD83C\uDDF7',
  CA: '\uD83C\uDDE8\uD83C\uDDE6',
}

export const COUNTRY_NAMES: Record<string, string> = {
  US: 'United States',
  UK: 'United Kingdom',
  GB: 'United Kingdom',
  DE: 'Germany',
  FR: 'France',
  JP: 'Japan',
  HK: 'Hong Kong',
  CN: 'China',
  KR: 'South Korea',
  IN: 'India',
  TW: 'Taiwan',
  AU: 'Australia',
  BR: 'Brazil',
  CA: 'Canada',
}

/** Maps country code to its primary index instrument ID for benchmark comparisons. */
export const COUNTRY_BENCHMARK_MAP: Record<string, string> = {
  US: 'SPX',
  UK: 'FTM',
  DE: 'DAX',
  FR: 'CAC',
  JP: 'NKX',
  HK: 'HSI',
  CN: 'CSI300',
  KR: 'KS11',
  IN: 'NSEI',
  TW: 'TWII',
  AU: 'AXJO',
  BR: 'BVSP',
  CA: 'GSPTSE',
}

export const MOCK_COUNTRY_DATA: RankingItem[] = [
  { instrument_id: 'SPX', name: 'S&P 500', country: 'US', sector: null, asset_type: 'country_index', rs_line: 112.5, rs_ma: 108.2, price_trend: 'OUTPERFORMING', rs_momentum_pct: 8.3, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'BUY', rs_score: 72.5, regime: 'RISK_ON' },
  { instrument_id: 'NKX', name: 'Nikkei 225', country: 'JP', sector: null, asset_type: 'country_index', rs_line: 110.1, rs_ma: 105.8, price_trend: 'OUTPERFORMING', rs_momentum_pct: 12.5, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'BUY', rs_score: 68.1, regime: 'RISK_ON' },
  { instrument_id: 'DAX', name: 'DAX 40', country: 'DE', sector: null, asset_type: 'country_index', rs_line: 106.3, rs_ma: 103.5, price_trend: 'OUTPERFORMING', rs_momentum_pct: 4.7, momentum_trend: 'ACCELERATING', volume_character: 'NEUTRAL', action: 'HOLD_FADING', rs_score: 61.3, regime: 'RISK_ON' },
  { instrument_id: 'TWII', name: 'TWSE', country: 'TW', sector: null, asset_type: 'country_index', rs_line: 104.8, rs_ma: 103.1, price_trend: 'OUTPERFORMING', rs_momentum_pct: -2.1, momentum_trend: 'DECELERATING', volume_character: 'NEUTRAL', action: 'HOLD_FADING', rs_score: 58.4, regime: 'RISK_ON' },
  { instrument_id: 'KS11', name: 'KOSPI', country: 'KR', sector: null, asset_type: 'country_index', rs_line: 103.2, rs_ma: 101.5, price_trend: 'OUTPERFORMING', rs_momentum_pct: -5.3, momentum_trend: 'DECELERATING', volume_character: 'DISTRIBUTION', action: 'REDUCE', rs_score: 55.2, regime: 'RISK_ON' },
  { instrument_id: 'CAC', name: 'CAC 40', country: 'FR', sector: null, asset_type: 'country_index', rs_line: 101.8, rs_ma: 100.9, price_trend: 'OUTPERFORMING', rs_momentum_pct: 1.8, momentum_trend: 'ACCELERATING', volume_character: 'NEUTRAL', action: 'HOLD_FADING', rs_score: 52.7, regime: 'RISK_ON' },
  { instrument_id: 'GSPTSE', name: 'TSX Composite', country: 'CA', sector: null, asset_type: 'country_index', rs_line: 98.6, rs_ma: 99.4, price_trend: 'UNDERPERFORMING', rs_momentum_pct: 3.2, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'ACCUMULATE', rs_score: 48.6, regime: 'RISK_ON' },
  { instrument_id: 'AXJO', name: 'ASX 200', country: 'AU', sector: null, asset_type: 'country_index', rs_line: 97.1, rs_ma: 98.8, price_trend: 'UNDERPERFORMING', rs_momentum_pct: -1.5, momentum_trend: 'DECELERATING', volume_character: 'NEUTRAL', action: 'AVOID', rs_score: 45.1, regime: 'RISK_ON' },
  { instrument_id: 'BVSP', name: 'IBOVESPA', country: 'BR', sector: null, asset_type: 'country_index', rs_line: 95.3, rs_ma: 97.2, price_trend: 'UNDERPERFORMING', rs_momentum_pct: 7.8, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'WATCH', rs_score: 42.3, regime: 'RISK_ON' },
  { instrument_id: 'HSI', name: 'Hang Seng', country: 'HK', sector: null, asset_type: 'country_index', rs_line: 93.5, rs_ma: 96.1, price_trend: 'UNDERPERFORMING', rs_momentum_pct: 2.4, momentum_trend: 'ACCELERATING', volume_character: 'NEUTRAL', action: 'WATCH', rs_score: 38.5, regime: 'RISK_ON' },
  { instrument_id: 'FTM', name: 'FTSE 100', country: 'UK', sector: null, asset_type: 'country_index', rs_line: 91.2, rs_ma: 95.8, price_trend: 'UNDERPERFORMING', rs_momentum_pct: -8.4, momentum_trend: 'DECELERATING', volume_character: 'DISTRIBUTION', action: 'SELL', rs_score: 35.2, regime: 'RISK_ON' },
  { instrument_id: 'NSEI', name: 'NIFTY 50', country: 'IN', sector: null, asset_type: 'country_index', rs_line: 88.4, rs_ma: 96.5, price_trend: 'UNDERPERFORMING', rs_momentum_pct: -14.2, momentum_trend: 'DECELERATING', volume_character: 'DISTRIBUTION', action: 'SELL', rs_score: 28.5, regime: 'RISK_ON' },
  { instrument_id: 'CSI300', name: 'CSI 300', country: 'CN', sector: null, asset_type: 'country_index', rs_line: 86.9, rs_ma: 94.3, price_trend: 'UNDERPERFORMING', rs_momentum_pct: -12.1, momentum_trend: 'DECELERATING', volume_character: 'DISTRIBUTION', action: 'SELL', rs_score: 25.9, regime: 'RISK_ON' },
]
