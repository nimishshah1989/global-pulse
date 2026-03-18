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
  { instrument_id: 'SPX', name: 'S&P 500', country: 'US', sector: null, adjusted_rs_score: 72.5, rs_momentum: 8.3, quadrant: 'LEADING', rs_pct_1m: 68, rs_pct_3m: 75, rs_pct_6m: 80, rs_pct_12m: 65, volume_ratio: 1.15, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'NKX', name: 'Nikkei 225', country: 'JP', sector: null, adjusted_rs_score: 68.1, rs_momentum: 12.5, quadrant: 'LEADING', rs_pct_1m: 72, rs_pct_3m: 70, rs_pct_6m: 66, rs_pct_12m: 62, volume_ratio: 1.22, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'NSEI', name: 'NIFTY 50', country: 'IN', sector: null, adjusted_rs_score: 65.8, rs_momentum: 6.1, quadrant: 'LEADING', rs_pct_1m: 60, rs_pct_3m: 68, rs_pct_6m: 72, rs_pct_12m: 58, volume_ratio: 1.08, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'DAX', name: 'DAX 40', country: 'DE', sector: null, adjusted_rs_score: 61.3, rs_momentum: 4.7, quadrant: 'LEADING', rs_pct_1m: 55, rs_pct_3m: 62, rs_pct_6m: 64, rs_pct_12m: 60, volume_ratio: 1.05, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'TWII', name: 'TWSE', country: 'TW', sector: null, adjusted_rs_score: 58.4, rs_momentum: -2.1, quadrant: 'WEAKENING', rs_pct_1m: 45, rs_pct_3m: 58, rs_pct_6m: 62, rs_pct_12m: 70, volume_ratio: 0.95, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'KS11', name: 'KOSPI', country: 'KR', sector: null, adjusted_rs_score: 55.2, rs_momentum: -5.3, quadrant: 'WEAKENING', rs_pct_1m: 42, rs_pct_3m: 55, rs_pct_6m: 58, rs_pct_12m: 52, volume_ratio: 0.88, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'CAC', name: 'CAC 40', country: 'FR', sector: null, adjusted_rs_score: 52.7, rs_momentum: 1.8, quadrant: 'LEADING', rs_pct_1m: 50, rs_pct_3m: 52, rs_pct_6m: 54, rs_pct_12m: 55, volume_ratio: 1.02, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'GSPTSE', name: 'TSX Composite', country: 'CA', sector: null, adjusted_rs_score: 48.6, rs_momentum: 3.2, quadrant: 'IMPROVING', rs_pct_1m: 52, rs_pct_3m: 48, rs_pct_6m: 45, rs_pct_12m: 50, volume_ratio: 0.97, rs_trend: 'UNDERPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'AXJO', name: 'ASX 200', country: 'AU', sector: null, adjusted_rs_score: 45.1, rs_momentum: -1.5, quadrant: 'LAGGING', rs_pct_1m: 38, rs_pct_3m: 45, rs_pct_6m: 48, rs_pct_12m: 46, volume_ratio: 0.92, rs_trend: 'UNDERPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'BVSP', name: 'IBOVESPA', country: 'BR', sector: null, adjusted_rs_score: 42.3, rs_momentum: 7.8, quadrant: 'IMPROVING', rs_pct_1m: 58, rs_pct_3m: 42, rs_pct_6m: 38, rs_pct_12m: 35, volume_ratio: 1.18, rs_trend: 'UNDERPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'HSI', name: 'Hang Seng', country: 'HK', sector: null, adjusted_rs_score: 38.5, rs_momentum: 2.4, quadrant: 'IMPROVING', rs_pct_1m: 48, rs_pct_3m: 38, rs_pct_6m: 35, rs_pct_12m: 32, volume_ratio: 1.10, rs_trend: 'UNDERPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'FTM', name: 'FTSE 100', country: 'UK', sector: null, adjusted_rs_score: 35.2, rs_momentum: -8.4, quadrant: 'LAGGING', rs_pct_1m: 30, rs_pct_3m: 35, rs_pct_6m: 40, rs_pct_12m: 42, volume_ratio: 0.82, rs_trend: 'UNDERPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'CSI300', name: 'CSI 300', country: 'CN', sector: null, adjusted_rs_score: 28.9, rs_momentum: -12.1, quadrant: 'LAGGING', rs_pct_1m: 22, rs_pct_3m: 28, rs_pct_6m: 32, rs_pct_12m: 30, volume_ratio: 0.75, rs_trend: 'UNDERPERFORMING', liquidity_tier: 1, extension_warning: false },
]
