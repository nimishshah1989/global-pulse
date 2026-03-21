import type { Action } from '@/types/rs'
import { actionLabel, watchSubLabel } from '@/types/rs'

interface ActionFilterProps {
  value: Action | null
  onChange: (action: Action | null) => void
}

const ACTIONS: Action[] = ['BUY', 'HOLD', 'WATCH_EMERGING', 'WATCH_RELATIVE', 'WATCH_EARLY', 'AVOID', 'SELL']

const ACTION_PILL_COLORS: Record<Action, { active: string; inactive: string }> = {
  BUY:            { active: 'bg-emerald-600 text-white', inactive: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100' },
  HOLD:           { active: 'bg-amber-500 text-white',   inactive: 'bg-amber-50 text-amber-700 hover:bg-amber-100' },
  WATCH_EMERGING: { active: 'bg-blue-600 text-white',    inactive: 'bg-blue-50 text-blue-700 hover:bg-blue-100' },
  WATCH_RELATIVE: { active: 'bg-sky-600 text-white',     inactive: 'bg-sky-50 text-sky-700 hover:bg-sky-100' },
  WATCH_EARLY:    { active: 'bg-indigo-600 text-white',  inactive: 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100' },
  AVOID:          { active: 'bg-orange-600 text-white',  inactive: 'bg-orange-50 text-orange-700 hover:bg-orange-100' },
  SELL:           { active: 'bg-red-600 text-white',     inactive: 'bg-red-50 text-red-700 hover:bg-red-100' },
}

export default function ActionFilter({ value, onChange }: ActionFilterProps): JSX.Element {
  return (
    <div className="flex items-center gap-1 flex-wrap">
      <button
        onClick={() => onChange(null)}
        className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
          value === null
            ? 'bg-slate-700 text-white'
            : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
        }`}
      >
        All
      </button>
      {ACTIONS.map((action) => {
        const colors = ACTION_PILL_COLORS[action]
        const isActive = value === action
        const sub = watchSubLabel(action)
        const label = `${actionLabel(action)}${sub ? ` (${sub})` : ''}`

        return (
          <button
            key={action}
            onClick={() => onChange(isActive ? null : action)}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
              isActive ? colors.active : colors.inactive
            }`}
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}
