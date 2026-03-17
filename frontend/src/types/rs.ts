export type Quadrant = 'LEADING' | 'WEAKENING' | 'LAGGING' | 'IMPROVING'
export type Regime = 'RISK_ON' | 'RISK_OFF'

export interface RSScore {
  instrument_id: string
  date: string
  rs_line: number
  rs_ma_150: number
  rs_trend: 'OUTPERFORMING' | 'UNDERPERFORMING'
  rs_pct_1m: number
  rs_pct_3m: number
  rs_pct_6m: number
  rs_pct_12m: number
  rs_composite: number
  rs_momentum: number
  volume_ratio: number
  vol_multiplier: number
  adjusted_rs_score: number
  quadrant: Quadrant
  liquidity_tier: number
  extension_warning: boolean
  regime: Regime
}

export interface RankingItem {
  instrument_id: string
  name: string
  country: string | null
  sector: string | null
  adjusted_rs_score: number
  rs_momentum: number
  quadrant: Quadrant
  rs_pct_1m: number
  rs_pct_3m: number
  rs_pct_6m: number
  rs_pct_12m: number
  volume_ratio: number
  rs_trend: string
  liquidity_tier: number
  extension_warning: boolean
}

export interface RRGTrailPoint {
  date: string
  rs_score: number
  rs_momentum: number
}

export interface RRGDataPoint {
  id: string
  name: string
  rs_score: number
  rs_momentum: number
  quadrant: Quadrant
  trail: RRGTrailPoint[]
}
