import type { RankingItem, RRGDataPoint } from '@/types/rs'

export const MOCK_STOCK_DATA: RankingItem[] = [
  { instrument_id: 'NVDA_US', name: 'NVIDIA Corp', country: 'US', sector: 'technology', adjusted_rs_score: 92.4, rs_momentum: 18.3, quadrant: 'LEADING', rs_pct_1m: 96, rs_pct_3m: 97, rs_pct_6m: 95, rs_pct_12m: 91, volume_ratio: 1.45, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: true },
  { instrument_id: 'AVGO_US', name: 'Broadcom Inc', country: 'US', sector: 'technology', adjusted_rs_score: 85.1, rs_momentum: 14.2, quadrant: 'LEADING', rs_pct_1m: 88, rs_pct_3m: 85, rs_pct_6m: 82, rs_pct_12m: 80, volume_ratio: 1.32, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'META_US', name: 'Meta Platforms', country: 'US', sector: 'technology', adjusted_rs_score: 81.7, rs_momentum: 9.5, quadrant: 'LEADING', rs_pct_1m: 82, rs_pct_3m: 80, rs_pct_6m: 84, rs_pct_12m: 78, volume_ratio: 1.18, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'MSFT_US', name: 'Microsoft Corp', country: 'US', sector: 'technology', adjusted_rs_score: 76.3, rs_momentum: 5.8, quadrant: 'LEADING', rs_pct_1m: 72, rs_pct_3m: 76, rs_pct_6m: 78, rs_pct_12m: 75, volume_ratio: 1.10, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'AAPL_US', name: 'Apple Inc', country: 'US', sector: 'technology', adjusted_rs_score: 72.8, rs_momentum: 3.2, quadrant: 'LEADING', rs_pct_1m: 68, rs_pct_3m: 72, rs_pct_6m: 75, rs_pct_12m: 73, volume_ratio: 1.05, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'CRM_US', name: 'Salesforce Inc', country: 'US', sector: 'technology', adjusted_rs_score: 68.4, rs_momentum: 7.1, quadrant: 'LEADING', rs_pct_1m: 70, rs_pct_3m: 68, rs_pct_6m: 65, rs_pct_12m: 62, volume_ratio: 1.15, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'GOOG_US', name: 'Alphabet Inc', country: 'US', sector: 'technology', adjusted_rs_score: 64.2, rs_momentum: -2.3, quadrant: 'WEAKENING', rs_pct_1m: 55, rs_pct_3m: 64, rs_pct_6m: 68, rs_pct_12m: 70, volume_ratio: 0.95, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'ORCL_US', name: 'Oracle Corp', country: 'US', sector: 'technology', adjusted_rs_score: 61.5, rs_momentum: -5.1, quadrant: 'WEAKENING', rs_pct_1m: 48, rs_pct_3m: 60, rs_pct_6m: 64, rs_pct_12m: 68, volume_ratio: 0.88, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'ADBE_US', name: 'Adobe Inc', country: 'US', sector: 'technology', adjusted_rs_score: 58.9, rs_momentum: -7.4, quadrant: 'WEAKENING', rs_pct_1m: 42, rs_pct_3m: 58, rs_pct_6m: 62, rs_pct_12m: 65, volume_ratio: 0.82, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'NOW_US', name: 'ServiceNow Inc', country: 'US', sector: 'technology', adjusted_rs_score: 55.7, rs_momentum: 1.8, quadrant: 'LEADING', rs_pct_1m: 58, rs_pct_3m: 55, rs_pct_6m: 52, rs_pct_12m: 56, volume_ratio: 1.02, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'AMZN_US', name: 'Amazon.com Inc', country: 'US', sector: 'technology', adjusted_rs_score: 52.1, rs_momentum: 4.5, quadrant: 'LEADING', rs_pct_1m: 56, rs_pct_3m: 52, rs_pct_6m: 48, rs_pct_12m: 50, volume_ratio: 1.08, rs_trend: 'OUTPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'INTC_US', name: 'Intel Corp', country: 'US', sector: 'technology', adjusted_rs_score: 45.3, rs_momentum: 12.8, quadrant: 'IMPROVING', rs_pct_1m: 65, rs_pct_3m: 45, rs_pct_6m: 38, rs_pct_12m: 28, volume_ratio: 1.55, rs_trend: 'UNDERPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'QCOM_US', name: 'Qualcomm Inc', country: 'US', sector: 'technology', adjusted_rs_score: 42.6, rs_momentum: 6.3, quadrant: 'IMPROVING', rs_pct_1m: 52, rs_pct_3m: 42, rs_pct_6m: 40, rs_pct_12m: 38, volume_ratio: 1.12, rs_trend: 'UNDERPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'AMD_US', name: 'AMD Inc', country: 'US', sector: 'technology', adjusted_rs_score: 38.7, rs_momentum: -3.6, quadrant: 'LAGGING', rs_pct_1m: 35, rs_pct_3m: 38, rs_pct_6m: 42, rs_pct_12m: 45, volume_ratio: 0.92, rs_trend: 'UNDERPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'CSCO_US', name: 'Cisco Systems', country: 'US', sector: 'technology', adjusted_rs_score: 35.2, rs_momentum: -8.1, quadrant: 'LAGGING', rs_pct_1m: 28, rs_pct_3m: 35, rs_pct_6m: 40, rs_pct_12m: 42, volume_ratio: 0.78, rs_trend: 'UNDERPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'TXN_US', name: 'Texas Instruments', country: 'US', sector: 'technology', adjusted_rs_score: 32.8, rs_momentum: 2.4, quadrant: 'IMPROVING', rs_pct_1m: 40, rs_pct_3m: 32, rs_pct_6m: 30, rs_pct_12m: 35, volume_ratio: 0.98, rs_trend: 'UNDERPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'MU_US', name: 'Micron Technology', country: 'US', sector: 'technology', adjusted_rs_score: 28.5, rs_momentum: -11.2, quadrant: 'LAGGING', rs_pct_1m: 22, rs_pct_3m: 28, rs_pct_6m: 32, rs_pct_12m: 35, volume_ratio: 0.72, rs_trend: 'UNDERPERFORMING', liquidity_tier: 1, extension_warning: false },
  { instrument_id: 'PLTR_US', name: 'Palantir Tech', country: 'US', sector: 'technology', adjusted_rs_score: 25.1, rs_momentum: -5.7, quadrant: 'LAGGING', rs_pct_1m: 20, rs_pct_3m: 25, rs_pct_6m: 28, rs_pct_12m: 30, volume_ratio: 0.65, rs_trend: 'UNDERPERFORMING', liquidity_tier: 2, extension_warning: false },
  { instrument_id: 'SNAP_US', name: 'Snap Inc', country: 'US', sector: 'technology', adjusted_rs_score: 18.3, rs_momentum: -14.5, quadrant: 'LAGGING', rs_pct_1m: 12, rs_pct_3m: 18, rs_pct_6m: 22, rs_pct_12m: 25, volume_ratio: 0.58, rs_trend: 'UNDERPERFORMING', liquidity_tier: 2, extension_warning: false },
  { instrument_id: 'PINS_US', name: 'Pinterest Inc', country: 'US', sector: 'technology', adjusted_rs_score: 15.6, rs_momentum: 3.8, quadrant: 'IMPROVING', rs_pct_1m: 25, rs_pct_3m: 15, rs_pct_6m: 12, rs_pct_12m: 18, volume_ratio: 0.85, rs_trend: 'UNDERPERFORMING', liquidity_tier: 2, extension_warning: false },
]

export function getMockStockRRGData(): RRGDataPoint[] {
  return MOCK_STOCK_DATA.map((s) => ({
    id: s.instrument_id,
    name: s.name,
    rs_score: s.adjusted_rs_score,
    rs_momentum: s.rs_momentum,
    quadrant: s.quadrant,
    trail: generateStockTrail(s.adjusted_rs_score, s.rs_momentum),
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
