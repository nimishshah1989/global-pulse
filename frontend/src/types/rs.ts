// Actions — matching MarketPulse 3-gate engine exactly
export type Action =
  | 'BUY'
  | 'HOLD'
  | 'WATCH_EMERGING'
  | 'WATCH_RELATIVE'
  | 'WATCH_EARLY'
  | 'AVOID'
  | 'SELL'

export type Quadrant = 'LEADING' | 'WEAKENING' | 'IMPROVING' | 'LAGGING'
export type VolumeSignal = 'ACCUMULATION' | 'WEAK_RALLY' | 'DISTRIBUTION' | 'WEAK_DECLINE'
export type MarketRegime = 'BULL' | 'CAUTIOUS' | 'CORRECTION' | 'BEAR'
export type Regime = MarketRegime

export function isWatch(action: Action): boolean {
  return action === 'WATCH_EMERGING' || action === 'WATCH_RELATIVE' || action === 'WATCH_EARLY'
}

export function actionLabel(action: Action): string {
  if (isWatch(action)) return 'Watch'
  const labels: Record<string, string> = { BUY: 'Buy', HOLD: 'Hold', AVOID: 'Avoid', SELL: 'Sell' }
  return labels[action] ?? action
}

export function watchSubLabel(action: Action): string | null {
  if (action === 'WATCH_EMERGING') return 'Emerging'
  if (action === 'WATCH_RELATIVE') return 'Relative'
  if (action === 'WATCH_EARLY') return 'Early'
  return null
}

export function volumeLabel(signal: VolumeSignal | null): string {
  if (!signal) return '--'
  const map: Record<VolumeSignal, string> = {
    ACCUMULATION: 'Accumulation',
    WEAK_RALLY: 'Weak Rally',
    DISTRIBUTION: 'Distribution',
    WEAK_DECLINE: 'Weak Decline',
  }
  return map[signal] ?? signal
}

export function regimeLabel(regime: MarketRegime): string {
  const map: Record<MarketRegime, string> = {
    BULL: 'Bull',
    CAUTIOUS: 'Cautious',
    CORRECTION: 'Correction',
    BEAR: 'Bear',
  }
  return map[regime] ?? regime
}

export interface RankingItem {
  instrument_id: string
  name: string
  country: string | null
  sector: string | null
  asset_type: string | null
  // RS data
  rs_score: number
  rs_momentum: number | null
  // Quadrant
  quadrant: Quadrant | null
  // 3-gate action
  action: Action
  action_reason: string | null
  // Volume
  volume_signal: VolumeSignal | null
  // Regime
  regime: MarketRegime
  // Ratio returns (actual %)
  absolute_return: number | null
  relative_return: number | null
  return_1m: number | null
  return_3m: number | null
  return_6m: number | null
  return_12m: number | null
  // Excess returns vs benchmark
  excess_1m: number | null
  excess_3m: number | null
  excess_6m: number | null
  excess_12m: number | null
  // Benchmark
  benchmark_id: string | null
}
