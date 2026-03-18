import type { Action } from '@/types/rs'

interface FilterBarProps {
  selectedActions: Action[]
  onActionsChange: (actions: Action[]) => void
  rsMinimum: number
  onRsMinimumChange: (value: number) => void
}

const ACTIONS: { value: Action; label: string; color: string }[] = [
  { value: 'BUY', label: 'Buy', color: 'accent-emerald-600' },
  { value: 'ACCUMULATE', label: 'Accumulate', color: 'accent-teal-600' },
  { value: 'HOLD_DIVERGENCE', label: 'Hold (Divergence)', color: 'accent-yellow-600' },
  { value: 'HOLD_FADING', label: 'Hold (Fading)', color: 'accent-yellow-600' },
  { value: 'REDUCE', label: 'Reduce', color: 'accent-orange-600' },
  { value: 'SELL', label: 'Sell', color: 'accent-red-600' },
  { value: 'WATCH', label: 'Watch', color: 'accent-blue-600' },
  { value: 'AVOID', label: 'Avoid', color: 'accent-slate-600' },
]

export default function FilterBar({
  selectedActions,
  onActionsChange,
  rsMinimum,
  onRsMinimumChange,
}: FilterBarProps): JSX.Element {
  function handleActionToggle(action: Action): void {
    if (selectedActions.includes(action)) {
      onActionsChange(selectedActions.filter((a) => a !== action))
    } else {
      onActionsChange([...selectedActions, action])
    }
  }

  return (
    <div
      className="flex flex-wrap items-center gap-6 rounded-xl border border-slate-200 bg-white px-5 py-3"
      data-testid="filter-bar"
    >
      {/* Action filter */}
      <div className="flex items-center gap-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Action
        </span>
        <div className="flex flex-wrap items-center gap-2">
          {ACTIONS.map((a) => (
            <label
              key={a.value}
              className="flex cursor-pointer items-center gap-1.5 text-sm text-slate-700"
            >
              <input
                type="checkbox"
                checked={selectedActions.includes(a.value)}
                onChange={() => handleActionToggle(a.value)}
                className={`h-3.5 w-3.5 rounded border-slate-300 ${a.color}`}
                data-testid={`action-${a.value}`}
              />
              {a.label}
            </label>
          ))}
        </div>
      </div>

      {/* RS minimum slider */}
      <div className="flex items-center gap-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          RS Min
        </span>
        <input
          type="range"
          min={0}
          max={100}
          value={rsMinimum}
          onChange={(e) => onRsMinimumChange(Number(e.target.value))}
          className="h-1.5 w-24 cursor-pointer appearance-none rounded-full bg-slate-200 accent-teal-600"
          data-testid="rs-minimum-slider"
        />
        <span className="font-mono text-sm font-medium text-slate-700">{rsMinimum}</span>
      </div>
    </div>
  )
}
