export interface Instrument {
  id: string
  name: string
  ticker_stooq: string | null
  ticker_yfinance: string | null
  source: 'stooq' | 'yfinance'
  asset_type: string
  country: string | null
  sector: string | null
  hierarchy_level: number
  benchmark_id: string | null
  currency: string
  liquidity_tier: number
  is_active: boolean
}
