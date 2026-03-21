import type { Action } from '@/types/rs'
import { actionLabel, watchSubLabel } from '@/types/rs'

interface ActionBadgeProps {
  action: Action
}

const ACTION_STYLES: Record<Action, { bg: string; text: string }> = {
  BUY:            { bg: 'bg-emerald-100', text: 'text-emerald-700' },
  HOLD:           { bg: 'bg-amber-100',   text: 'text-amber-700' },
  WATCH_EMERGING: { bg: 'bg-blue-100',    text: 'text-blue-700' },
  WATCH_RELATIVE: { bg: 'bg-sky-100',     text: 'text-sky-700' },
  WATCH_EARLY:    { bg: 'bg-indigo-100',  text: 'text-indigo-700' },
  AVOID:          { bg: 'bg-orange-100',   text: 'text-orange-700' },
  SELL:           { bg: 'bg-red-100',      text: 'text-red-700' },
}

export default function ActionBadge({ action }: ActionBadgeProps): JSX.Element {
  const style = ACTION_STYLES[action] ?? { bg: 'bg-slate-100', text: 'text-slate-600' }
  const sub = watchSubLabel(action)
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${style.bg} ${style.text}`}>
      {actionLabel(action)}{sub ? ` (${sub})` : ''}
    </span>
  )
}

export { ActionBadge as QuadrantBadge }
export function QuadrantBadgeCompat({ quadrant }: { quadrant: string }): JSX.Element {
  return <ActionBadge action={quadrant as Action} />
}
