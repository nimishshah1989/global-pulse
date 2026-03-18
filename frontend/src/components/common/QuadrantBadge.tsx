import type { Action } from '@/types/rs'

interface ActionBadgeProps {
  action: Action
}

const ACTION_STYLES: Record<Action, { bg: string; text: string; label: string }> = {
  BUY: { bg: 'bg-emerald-100', text: 'text-emerald-700', label: '\u25B2 Buy' },
  HOLD_DIVERGENCE: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: '\u2014 Hold' },
  HOLD_FADING: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: '\u2014 Hold' },
  REDUCE: { bg: 'bg-orange-100', text: 'text-orange-700', label: '\u25BC Reduce' },
  SELL: { bg: 'bg-red-100', text: 'text-red-700', label: '\u25BC Sell' },
  WATCH: { bg: 'bg-blue-100', text: 'text-blue-700', label: '\u25C9 Watch' },
  ACCUMULATE: { bg: 'bg-teal-100', text: 'text-teal-700', label: '\u25B2 Accumulate' },
  AVOID: { bg: 'bg-slate-100', text: 'text-slate-600', label: '\u2715 Avoid' },
}

export default function ActionBadge({ action }: ActionBadgeProps): JSX.Element {
  const style = ACTION_STYLES[action] ?? ACTION_STYLES.WATCH
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${style.bg} ${style.text}`}>
      {style.label}
    </span>
  )
}

// Keep old name as alias for backward compat
export { ActionBadge as QuadrantBadge }
export function QuadrantBadgeCompat({ quadrant }: { quadrant: string }): JSX.Element {
  return <ActionBadge action={quadrant as Action} />
}
