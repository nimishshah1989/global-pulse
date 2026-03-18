import type { Basket, BasketPosition, BasketNAV, BasketPerformance } from '@/types/baskets'
import type { RankingItem } from '@/types/rs'

export const MOCK_BASKETS: Basket[] = [
  {
    id: 'basket-asia-momentum',
    name: 'Asia Momentum Leaders',
    description: 'Top momentum stocks across Japan, Taiwan, and India',
    benchmark_id: 'ACWI',
    created_at: '2025-12-17T00:00:00Z',
    status: 'active',
    weighting_method: 'equal',
  },
  {
    id: 'basket-us-tech',
    name: 'US Tech Breakouts',
    description: 'US technology sector leaders with volume confirmation',
    benchmark_id: 'SPX',
    created_at: '2026-01-10T00:00:00Z',
    status: 'active',
    weighting_method: 'rs_weighted',
  },
  {
    id: 'basket-em-recovery',
    name: 'EM Recovery Play',
    description: 'Emerging market improving action bets',
    benchmark_id: 'ACWI',
    created_at: '2026-02-20T00:00:00Z',
    status: 'active',
    weighting_method: 'equal',
  },
]

export const MOCK_BASKET_POSITIONS: BasketPosition[] = [
  { id: 'pos-1', basket_id: 'basket-asia-momentum', instrument_id: 'EWJ_US', weight: 0.3333, added_at: '2025-12-17T00:00:00Z', removed_at: null, status: 'active' },
  { id: 'pos-2', basket_id: 'basket-asia-momentum', instrument_id: 'EWT_US', weight: 0.3333, added_at: '2025-12-17T00:00:00Z', removed_at: null, status: 'active' },
  { id: 'pos-3', basket_id: 'basket-asia-momentum', instrument_id: 'INDA_US', weight: 0.3334, added_at: '2025-12-17T00:00:00Z', removed_at: null, status: 'active' },
]

export const MOCK_POSITION_DETAILS: (RankingItem & { weight: number; position_return: number })[] = [
  { instrument_id: 'EWJ_US', name: 'iShares MSCI Japan', country: 'JP', sector: null, asset_type: 'country_etf', rs_line: 105.2, rs_ma: 100.8, price_trend: 'OUTPERFORMING', rs_momentum_pct: 12.5, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'BUY', rs_score: 68.1, regime: 'RISK_ON', weight: 0.3333, position_return: 14.2 },
  { instrument_id: 'EWT_US', name: 'iShares MSCI Taiwan', country: 'TW', sector: null, asset_type: 'country_etf', rs_line: 101.4, rs_ma: 102.1, price_trend: 'UNDERPERFORMING', rs_momentum_pct: -2.1, momentum_trend: 'DECELERATING', volume_character: 'NEUTRAL', action: 'HOLD_FADING', rs_score: 58.4, regime: 'RISK_ON', weight: 0.3333, position_return: 8.7 },
  { instrument_id: 'INDA_US', name: 'iShares MSCI India', country: 'IN', sector: null, asset_type: 'country_etf', rs_line: 104.1, rs_ma: 101.5, price_trend: 'OUTPERFORMING', rs_momentum_pct: 6.1, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'ACCUMULATE', rs_score: 65.8, regime: 'RISK_ON', weight: 0.3334, position_return: 11.5 },
]

export const MOCK_BASKET_PERFORMANCE: BasketPerformance = {
  cumulative_return: 11.47,
  cagr: null,
  max_drawdown: -6.82,
  sharpe_ratio: 1.24,
  pct_weeks_outperforming: 58.3,
}

export function generateMockNAVHistory(): BasketNAV[] {
  const data: BasketNAV[] = []
  let nav = 100
  let benchmarkNav = 100

  for (let i = 90; i >= 0; i--) {
    const date = new Date()
    date.setDate(date.getDate() - i)
    // Skip weekends
    if (date.getDay() === 0 || date.getDay() === 6) continue

    nav += (Math.random() - 0.46) * 1.2
    benchmarkNav += (Math.random() - 0.47) * 1.0
    nav = Math.max(90, nav)
    benchmarkNav = Math.max(90, benchmarkNav)

    data.push({
      date: date.toISOString().split('T')[0],
      nav: Math.round(nav * 100) / 100,
      benchmark_nav: Math.round(benchmarkNav * 100) / 100,
      rs_line: Math.round((nav / benchmarkNav) * 100 * 100) / 100,
    })
  }
  return data
}
