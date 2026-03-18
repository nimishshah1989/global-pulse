import type { RankingItem, RRGDataPoint } from '@/types/rs'

export const MOCK_STOCK_DATA: RankingItem[] = [
  { instrument_id: 'NVDA_US', name: 'NVIDIA Corp', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 115.4, rs_ma: 105.2, price_trend: 'OUTPERFORMING', rs_momentum_pct: 18.3, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'BUY', rs_score: 92.4, regime: 'RISK_ON' },
  { instrument_id: 'AVGO_US', name: 'Broadcom Inc', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 112.1, rs_ma: 104.8, price_trend: 'OUTPERFORMING', rs_momentum_pct: 14.2, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'BUY', rs_score: 85.1, regime: 'RISK_ON' },
  { instrument_id: 'META_US', name: 'Meta Platforms', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 110.7, rs_ma: 104.2, price_trend: 'OUTPERFORMING', rs_momentum_pct: 9.5, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'BUY', rs_score: 81.7, regime: 'RISK_ON' },
  { instrument_id: 'MSFT_US', name: 'Microsoft Corp', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 108.3, rs_ma: 103.5, price_trend: 'OUTPERFORMING', rs_momentum_pct: 5.8, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'BUY', rs_score: 76.3, regime: 'RISK_ON' },
  { instrument_id: 'AAPL_US', name: 'Apple Inc', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 106.8, rs_ma: 103.1, price_trend: 'OUTPERFORMING', rs_momentum_pct: 3.2, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'BUY', rs_score: 72.8, regime: 'RISK_ON' },
  { instrument_id: 'CRM_US', name: 'Salesforce Inc', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 105.4, rs_ma: 102.8, price_trend: 'OUTPERFORMING', rs_momentum_pct: 7.1, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'BUY', rs_score: 68.4, regime: 'RISK_ON' },
  { instrument_id: 'GOOG_US', name: 'Alphabet Inc', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 104.2, rs_ma: 102.5, price_trend: 'OUTPERFORMING', rs_momentum_pct: -2.3, momentum_trend: 'DECELERATING', volume_character: 'DISTRIBUTION', action: 'REDUCE', rs_score: 64.2, regime: 'RISK_ON' },
  { instrument_id: 'ORCL_US', name: 'Oracle Corp', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 103.5, rs_ma: 102.2, price_trend: 'OUTPERFORMING', rs_momentum_pct: -5.1, momentum_trend: 'DECELERATING', volume_character: 'DISTRIBUTION', action: 'REDUCE', rs_score: 61.5, regime: 'RISK_ON' },
  { instrument_id: 'ADBE_US', name: 'Adobe Inc', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 102.9, rs_ma: 101.8, price_trend: 'OUTPERFORMING', rs_momentum_pct: -7.4, momentum_trend: 'DECELERATING', volume_character: 'DISTRIBUTION', action: 'REDUCE', rs_score: 58.9, regime: 'RISK_ON' },
  { instrument_id: 'NOW_US', name: 'ServiceNow Inc', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 101.7, rs_ma: 101.2, price_trend: 'OUTPERFORMING', rs_momentum_pct: 1.8, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'BUY', rs_score: 55.7, regime: 'RISK_ON' },
  { instrument_id: 'AMZN_US', name: 'Amazon.com Inc', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 101.1, rs_ma: 100.8, price_trend: 'OUTPERFORMING', rs_momentum_pct: 4.5, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'BUY', rs_score: 52.1, regime: 'RISK_ON' },
  { instrument_id: 'INTC_US', name: 'Intel Corp', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 96.3, rs_ma: 98.5, price_trend: 'UNDERPERFORMING', rs_momentum_pct: 12.8, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'ACCUMULATE', rs_score: 45.3, regime: 'RISK_ON' },
  { instrument_id: 'QCOM_US', name: 'Qualcomm Inc', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 95.6, rs_ma: 98.2, price_trend: 'UNDERPERFORMING', rs_momentum_pct: 6.3, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'ACCUMULATE', rs_score: 42.6, regime: 'RISK_ON' },
  { instrument_id: 'AMD_US', name: 'AMD Inc', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 94.7, rs_ma: 97.8, price_trend: 'UNDERPERFORMING', rs_momentum_pct: -3.6, momentum_trend: 'DECELERATING', volume_character: 'DISTRIBUTION', action: 'SELL', rs_score: 38.7, regime: 'RISK_ON' },
  { instrument_id: 'CSCO_US', name: 'Cisco Systems', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 93.2, rs_ma: 97.5, price_trend: 'UNDERPERFORMING', rs_momentum_pct: -8.1, momentum_trend: 'DECELERATING', volume_character: 'DISTRIBUTION', action: 'SELL', rs_score: 35.2, regime: 'RISK_ON' },
  { instrument_id: 'TXN_US', name: 'Texas Instruments', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 92.8, rs_ma: 97.2, price_trend: 'UNDERPERFORMING', rs_momentum_pct: 2.4, momentum_trend: 'ACCELERATING', volume_character: 'DISTRIBUTION', action: 'AVOID', rs_score: 32.8, regime: 'RISK_ON' },
  { instrument_id: 'MU_US', name: 'Micron Technology', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 91.5, rs_ma: 96.8, price_trend: 'UNDERPERFORMING', rs_momentum_pct: -11.2, momentum_trend: 'DECELERATING', volume_character: 'DISTRIBUTION', action: 'SELL', rs_score: 28.5, regime: 'RISK_ON' },
  { instrument_id: 'PLTR_US', name: 'Palantir Tech', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 90.1, rs_ma: 96.5, price_trend: 'UNDERPERFORMING', rs_momentum_pct: -5.7, momentum_trend: 'DECELERATING', volume_character: 'DISTRIBUTION', action: 'SELL', rs_score: 25.1, regime: 'RISK_ON' },
  { instrument_id: 'SNAP_US', name: 'Snap Inc', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 88.3, rs_ma: 95.8, price_trend: 'UNDERPERFORMING', rs_momentum_pct: -14.5, momentum_trend: 'DECELERATING', volume_character: 'DISTRIBUTION', action: 'SELL', rs_score: 18.3, regime: 'RISK_ON' },
  { instrument_id: 'PINS_US', name: 'Pinterest Inc', country: 'US', sector: 'technology', asset_type: 'stock', rs_line: 87.6, rs_ma: 95.5, price_trend: 'UNDERPERFORMING', rs_momentum_pct: 3.8, momentum_trend: 'ACCELERATING', volume_character: 'ACCUMULATION', action: 'ACCUMULATE', rs_score: 15.6, regime: 'RISK_ON' },
]

export function getMockStockRRGData(): RRGDataPoint[] {
  return MOCK_STOCK_DATA.map((s) => ({
    id: s.instrument_id,
    name: s.name,
    rs_score: s.rs_score,
    rs_momentum: s.rs_momentum_pct ?? 0,
    action: s.action,
    volume_character: s.volume_character,
    trail: generateStockTrail(s.rs_score, s.rs_momentum_pct ?? 0),
  }))
}

function generateStockTrail(
  currentX: number,
  currentY: number,
): RRGDataPoint['trail'] {
  const trail: RRGDataPoint['trail'] = []
  let x = currentX - currentY * 0.4 + (Math.random() - 0.5) * 10
  let y = currentY - 5 + (Math.random() - 0.5) * 8

  for (let i = 5; i >= 1; i--) {
    const date = new Date()
    date.setDate(date.getDate() - i * 7)
    x += (currentX - x) * 0.3 + (Math.random() - 0.5) * 2
    y += (currentY - y) * 0.3 + (Math.random() - 0.5) * 1.5
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
