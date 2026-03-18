export type Action = 'BUY' | 'HOLD_DIVERGENCE' | 'HOLD_FADING' | 'REDUCE' | 'SELL' | 'WATCH' | 'ACCUMULATE' | 'AVOID'
export type PriceTrend = 'OUTPERFORMING' | 'UNDERPERFORMING'
export type MomentumTrend = 'ACCELERATING' | 'DECELERATING'
export type VolumeCharacter = 'ACCUMULATION' | 'DISTRIBUTION' | 'NEUTRAL'
export type Regime = 'RISK_ON' | 'RISK_OFF'

// Quadrant labels used for RRG scatter display
export type Quadrant = 'LEADING' | 'WEAKENING' | 'LAGGING' | 'IMPROVING'

export interface RankingItem {
  instrument_id: string
  name: string
  country: string | null
  sector: string | null
  asset_type: string | null
  // Indicator 1: Price Trend
  rs_line: number | null
  rs_ma: number | null
  price_trend: PriceTrend | null
  // Indicator 2: Momentum
  rs_momentum_pct: number | null
  momentum_trend: MomentumTrend | null
  // Indicator 3: OBV
  volume_character: VolumeCharacter | null
  // Action
  action: Action
  // Score for sorting
  rs_score: number
  // Regime
  regime: Regime
}

// Backward compat
export interface RSScore extends RankingItem {
  date: string
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
  action: Action | null
  volume_character: string | null
  trail: RRGTrailPoint[]
}
