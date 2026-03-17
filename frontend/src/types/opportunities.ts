export type SignalType =
  | 'quadrant_entry_leading'
  | 'quadrant_entry_improving'
  | 'volume_breakout'
  | 'multi_level_alignment'
  | 'bearish_divergence'
  | 'bullish_divergence'
  | 'regime_change'
  | 'extension_alert'

export interface Opportunity {
  id: string
  instrument_id: string
  instrument_name: string
  date: string
  signal_type: SignalType
  conviction_score: number
  description: string
  metadata: Record<string, unknown> | null
}
