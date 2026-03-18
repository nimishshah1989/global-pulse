import type { RankingItem, RRGDataPoint } from '@/types/rs'

export const MOCK_SECTOR_DATA: Record<string, RankingItem[]> = {
  US: [
    { instrument_id: 'XLK_US', name: 'Technology', country: 'US', sector: 'technology', asset_type: 'sector_etf', rs_line: 108.2, rs_ma: 102.5, price_trend: 'OUTPERFORMING', rs_momentum_pct: 10.5, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'BUY', rs_score: 78.2, regime: 'RISK_ON' },
    { instrument_id: 'XLF_US', name: 'Financials', country: 'US', sector: 'financials', asset_type: 'sector_etf', rs_line: 105.4, rs_ma: 101.8, price_trend: 'OUTPERFORMING', rs_momentum_pct: 5.2, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'BUY', rs_score: 65.4, regime: 'RISK_ON' },
    { instrument_id: 'XLV_US', name: 'Healthcare', country: 'US', sector: 'healthcare', asset_type: 'sector_etf', rs_line: 103.1, rs_ma: 101.2, price_trend: 'OUTPERFORMING', rs_momentum_pct: 3.8, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'BUY', rs_score: 62.1, regime: 'RISK_ON' },
    { instrument_id: 'XLI_US', name: 'Industrials', country: 'US', sector: 'industrials', asset_type: 'sector_etf', rs_line: 102.7, rs_ma: 101.5, price_trend: 'OUTPERFORMING', rs_momentum_pct: -1.3, momentum_trend: 'DECELERATING', volume_character: 'ACCUMULATION', action: 'HOLD_FADING', rs_score: 58.7, regime: 'RISK_ON' },
    { instrument_id: 'XLY_US', name: 'Consumer Disc.', country: 'US', sector: 'consumer-discretionary', asset_type: 'sector_etf', rs_line: 101.3, rs_ma: 100.8, price_trend: 'OUTPERFORMING', rs_momentum_pct: -4.7, momentum_trend: 'DECELERATING', volume_character: 'DISTRIBUTION', action: 'REDUCE', rs_score: 55.3, regime: 'RISK_ON' },
    { instrument_id: 'XLC_US', name: 'Communication', country: 'US', sector: 'communication-services', asset_type: 'sector_etf', rs_line: 101.8, rs_ma: 100.9, price_trend: 'OUTPERFORMING', rs_momentum_pct: 2.1, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'BUY', rs_score: 52.8, regime: 'RISK_ON' },
    { instrument_id: 'XLB_US', name: 'Materials', country: 'US', sector: 'materials', asset_type: 'sector_etf', rs_line: 97.6, rs_ma: 99.2, price_trend: 'UNDERPERFORMING', rs_momentum_pct: 6.4, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'ACCUMULATE', rs_score: 45.6, regime: 'RISK_ON' },
    { instrument_id: 'XLP_US', name: 'Consumer Staples', country: 'US', sector: 'consumer-staples', asset_type: 'sector_etf', rs_line: 96.1, rs_ma: 99.5, price_trend: 'UNDERPERFORMING', rs_momentum_pct: -3.5, momentum_trend: 'DECELERATING', volume_character: 'DISTRIBUTION', action: 'SELL', rs_score: 42.1, regime: 'RISK_ON' },
    { instrument_id: 'XLE_US', name: 'Energy', country: 'US', sector: 'energy', asset_type: 'sector_etf', rs_line: 95.4, rs_ma: 98.8, price_trend: 'UNDERPERFORMING', rs_momentum_pct: 8.2, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'ACCUMULATE', rs_score: 38.4, regime: 'RISK_ON' },
    { instrument_id: 'XLRE_US', name: 'Real Estate', country: 'US', sector: 'real-estate', asset_type: 'sector_etf', rs_line: 93.5, rs_ma: 98.2, price_trend: 'UNDERPERFORMING', rs_momentum_pct: -9.8, momentum_trend: 'DECELERATING', volume_character: 'DISTRIBUTION', action: 'SELL', rs_score: 32.5, regime: 'RISK_ON' },
    { instrument_id: 'XLU_US', name: 'Utilities', country: 'US', sector: 'utilities', asset_type: 'sector_etf', rs_line: 92.9, rs_ma: 97.8, price_trend: 'UNDERPERFORMING', rs_momentum_pct: -6.2, momentum_trend: 'DECELERATING', volume_character: 'DISTRIBUTION', action: 'SELL', rs_score: 28.9, regime: 'RISK_ON' },
  ],
}

function generateTrail(currentX: number, currentY: number): RRGDataPoint['trail'] {
  const trail: RRGDataPoint['trail'] = []
  let x = currentX
  let y = currentY
  for (let i = 7; i >= 0; i--) {
    const date = new Date()
    date.setDate(date.getDate() - i * 7)
    x = x - (currentX - x) * 0.15 + (Math.random() - 0.5) * 3
    y = y - (currentY - y) * 0.15 + (Math.random() - 0.5) * 2
    trail.push({
      date: date.toISOString().split('T')[0],
      rs_score: Math.max(5, Math.min(95, x)),
      rs_momentum: Math.max(-45, Math.min(45, y)),
    })
  }
  trail.push({
    date: new Date().toISOString().split('T')[0],
    rs_score: currentX,
    rs_momentum: currentY,
  })
  return trail
}

export function getMockRRGData(countryCode: string): RRGDataPoint[] {
  const sectors = MOCK_SECTOR_DATA[countryCode]
  if (!sectors) return []

  return sectors.map((s) => ({
    id: s.instrument_id,
    name: s.name,
    rs_score: s.rs_score,
    rs_momentum: s.rs_momentum_pct ?? 0,
    action: s.action,
    volume_character: s.volume_character,
    trail: generateTrail(s.rs_score, s.rs_momentum_pct ?? 0),
  }))
}

export function getMockRSLineData(): { date: string; rs_line: number; rs_ma_150: number; volume: number }[] {
  const data: { date: string; rs_line: number; rs_ma_150: number; volume: number }[] = []
  let rsLine = 95
  let rsMa = 98

  for (let i = 252; i >= 0; i--) {
    const date = new Date()
    date.setDate(date.getDate() - i)
    rsLine += (Math.random() - 0.48) * 2
    rsMa += (rsLine - rsMa) * 0.007
    const volume = Math.floor(5000000 + Math.random() * 10000000)
    data.push({
      date: date.toISOString().split('T')[0],
      rs_line: Math.round(rsLine * 100) / 100,
      rs_ma_150: Math.round(rsMa * 100) / 100,
      volume,
    })
  }
  return data
}
