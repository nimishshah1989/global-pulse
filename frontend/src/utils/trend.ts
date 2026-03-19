/**
 * Shared helpers for price trend and volume character display.
 *
 * Trend values: OUTPERFORMING | UNDERPERFORMING | RECOVERING | CONSOLIDATING
 * Volume values: ACCUMULATION | DISTRIBUTION | NEUTRAL
 */

export function getTrendLabel(trend: string | null): string {
  const map: Record<string, string> = {
    OUTPERFORMING: '\u25B2 Outperforming',
    UNDERPERFORMING: '\u25BC Underperforming',
    RECOVERING: '\u25B3 Recovering',
    CONSOLIDATING: '\u25BD Consolidating',
  }
  return map[trend ?? ''] ?? '\u2014'
}

export function getTrendLabelShort(trend: string | null): string {
  const map: Record<string, string> = {
    OUTPERFORMING: '\u25B2 Out',
    UNDERPERFORMING: '\u25BC Under',
    RECOVERING: '\u25B3 Recov',
    CONSOLIDATING: '\u25BD Consol',
  }
  return map[trend ?? ''] ?? '\u2014'
}

export function getTrendColor(trend: string | null): string {
  if (trend === 'OUTPERFORMING' || trend === 'ACCELERATING') return 'text-emerald-600'
  if (trend === 'UNDERPERFORMING' || trend === 'DECELERATING') return 'text-red-600'
  if (trend === 'RECOVERING') return 'text-amber-600'
  if (trend === 'CONSOLIDATING') return 'text-blue-600'
  return 'text-slate-400'
}

export function getTrendArrow(trend: string | null): string {
  if (trend === 'OUTPERFORMING' || trend === 'ACCELERATING') return '\u25B2'
  if (trend === 'UNDERPERFORMING' || trend === 'DECELERATING') return '\u25BC'
  if (trend === 'RECOVERING') return '\u25B3'
  if (trend === 'CONSOLIDATING') return '\u25BD'
  return '\u2014'
}

export function getVolumeColor(character: string | null): string {
  if (character === 'ACCUMULATION') return 'text-emerald-600'
  if (character === 'DISTRIBUTION') return 'text-red-500'
  return 'text-slate-500'
}
