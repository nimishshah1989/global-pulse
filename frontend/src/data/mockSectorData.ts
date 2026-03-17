import type { RankingItem, RRGDataPoint } from '@/types/rs'

export const MOCK_SECTOR_DATA: Record<string, RankingItem[]> = {
  US: [
    { instrument_id: 'XLK_US', name: 'Technology', country: 'US', sector: 'technology', adjusted_rs_score: 78.2, rs_momentum: 10.5, quadrant: 'LEADING', rs_pct_1m: 80, rs_pct_3m: 76, rs_pct_6m: 82, rs_pct_12m: 74, volume_ratio: 1.25, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
    { instrument_id: 'XLF_US', name: 'Financials', country: 'US', sector: 'financials', adjusted_rs_score: 65.4, rs_momentum: 5.2, quadrant: 'LEADING', rs_pct_1m: 62, rs_pct_3m: 66, rs_pct_6m: 68, rs_pct_12m: 60, volume_ratio: 1.12, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
    { instrument_id: 'XLV_US', name: 'Healthcare', country: 'US', sector: 'healthcare', adjusted_rs_score: 62.1, rs_momentum: 3.8, quadrant: 'LEADING', rs_pct_1m: 58, rs_pct_3m: 60, rs_pct_6m: 65, rs_pct_12m: 62, volume_ratio: 1.05, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
    { instrument_id: 'XLI_US', name: 'Industrials', country: 'US', sector: 'industrials', adjusted_rs_score: 58.7, rs_momentum: -1.3, quadrant: 'WEAKENING', rs_pct_1m: 50, rs_pct_3m: 58, rs_pct_6m: 60, rs_pct_12m: 65, volume_ratio: 0.98, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
    { instrument_id: 'XLY_US', name: 'Consumer Disc.', country: 'US', sector: 'consumer-discretionary', adjusted_rs_score: 55.3, rs_momentum: -4.7, quadrant: 'WEAKENING', rs_pct_1m: 42, rs_pct_3m: 55, rs_pct_6m: 58, rs_pct_12m: 60, volume_ratio: 0.90, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
    { instrument_id: 'XLC_US', name: 'Communication', country: 'US', sector: 'communication-services', adjusted_rs_score: 52.8, rs_momentum: 2.1, quadrant: 'LEADING', rs_pct_1m: 55, rs_pct_3m: 52, rs_pct_6m: 50, rs_pct_12m: 54, volume_ratio: 1.03, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
    { instrument_id: 'XLB_US', name: 'Materials', country: 'US', sector: 'materials', adjusted_rs_score: 45.6, rs_momentum: 6.4, quadrant: 'IMPROVING', rs_pct_1m: 55, rs_pct_3m: 45, rs_pct_6m: 42, rs_pct_12m: 40, volume_ratio: 1.15, rs_trend: 'UNDERPERFORMING', liquidity_tier: 1, extension_warning: false },
    { instrument_id: 'XLP_US', name: 'Consumer Staples', country: 'US', sector: 'consumer-staples', adjusted_rs_score: 42.1, rs_momentum: -3.5, quadrant: 'LAGGING', rs_pct_1m: 35, rs_pct_3m: 42, rs_pct_6m: 45, rs_pct_12m: 48, volume_ratio: 0.85, rs_trend: 'UNDERPERFORMING', liquidity_tier: 1, extension_warning: false },
    { instrument_id: 'XLE_US', name: 'Energy', country: 'US', sector: 'energy', adjusted_rs_score: 38.4, rs_momentum: 8.2, quadrant: 'IMPROVING', rs_pct_1m: 60, rs_pct_3m: 38, rs_pct_6m: 35, rs_pct_12m: 30, volume_ratio: 1.30, rs_trend: 'UNDERPERFORMING', liquidity_tier: 1, extension_warning: false },
    { instrument_id: 'XLRE_US', name: 'Real Estate', country: 'US', sector: 'real-estate', adjusted_rs_score: 32.5, rs_momentum: -9.8, quadrant: 'LAGGING', rs_pct_1m: 25, rs_pct_3m: 32, rs_pct_6m: 35, rs_pct_12m: 38, volume_ratio: 0.72, rs_trend: 'UNDERPERFORMING', liquidity_tier: 1, extension_warning: false },
    { instrument_id: 'XLU_US', name: 'Utilities', country: 'US', sector: 'utilities', adjusted_rs_score: 28.9, rs_momentum: -6.2, quadrant: 'LAGGING', rs_pct_1m: 28, rs_pct_3m: 30, rs_pct_6m: 28, rs_pct_12m: 32, volume_ratio: 0.68, rs_trend: 'UNDERPERFORMING', liquidity_tier: 1, extension_warning: false },
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
    rs_score: s.adjusted_rs_score,
    rs_momentum: s.rs_momentum,
    quadrant: s.quadrant,
    trail: generateTrail(s.adjusted_rs_score, s.rs_momentum),
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
