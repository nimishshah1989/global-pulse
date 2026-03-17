export interface Basket {
  id: string
  name: string
  description: string | null
  benchmark_id: string | null
  created_at: string
  status: 'active' | 'archived'
  weighting_method: 'equal' | 'manual' | 'rs_weighted'
}

export interface BasketPosition {
  id: string
  basket_id: string
  instrument_id: string
  weight: number
  added_at: string
  removed_at: string | null
  status: string
}

export interface BasketNAV {
  date: string
  nav: number
  benchmark_nav: number | null
  rs_line: number | null
}

export interface BasketPerformance {
  cumulative_return: number
  cagr: number | null
  max_drawdown: number
  sharpe_ratio: number | null
  pct_weeks_outperforming: number
}
