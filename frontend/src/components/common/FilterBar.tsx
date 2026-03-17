import type { Quadrant } from '@/types/rs'

interface FilterBarProps {
  selectedQuadrants: Quadrant[]
  onQuadrantsChange: (quadrants: Quadrant[]) => void
  liquidityTier: number | null
  onLiquidityChange: (tier: number | null) => void
  rsMinimum: number
  onRsMinimumChange: (value: number) => void
}

const QUADRANTS: { value: Quadrant; label: string; color: string }[] = [
  { value: 'LEADING', label: 'Leading', color: 'accent-emerald-600' },
  { value: 'WEAKENING', label: 'Weakening', color: 'accent-amber-600' },
  { value: 'LAGGING', label: 'Lagging', color: 'accent-red-600' },
  { value: 'IMPROVING', label: 'Improving', color: 'accent-blue-600' },
]

export default function FilterBar({
  selectedQuadrants,
  onQuadrantsChange,
  liquidityTier,
  onLiquidityChange,
  rsMinimum,
  onRsMinimumChange,
}: FilterBarProps): JSX.Element {
  function handleQuadrantToggle(quadrant: Quadrant): void {
    if (selectedQuadrants.includes(quadrant)) {
      onQuadrantsChange(selectedQuadrants.filter((q) => q !== quadrant))
    } else {
      onQuadrantsChange([...selectedQuadrants, quadrant])
    }
  }

  return (
    <div
      className="flex flex-wrap items-center gap-6 rounded-xl border border-slate-200 bg-white px-5 py-3"
      data-testid="filter-bar"
    >
      {/* Quadrant filter */}
      <div className="flex items-center gap-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Quadrant
        </span>
        <div className="flex items-center gap-2">
          {QUADRANTS.map((q) => (
            <label
              key={q.value}
              className="flex cursor-pointer items-center gap-1.5 text-sm text-slate-700"
            >
              <input
                type="checkbox"
                checked={selectedQuadrants.includes(q.value)}
                onChange={() => handleQuadrantToggle(q.value)}
                className={`h-3.5 w-3.5 rounded border-slate-300 ${q.color}`}
                data-testid={`quadrant-${q.value}`}
              />
              {q.label}
            </label>
          ))}
        </div>
      </div>

      {/* Liquidity filter */}
      <div className="flex items-center gap-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Liquidity
        </span>
        <select
          value={liquidityTier ?? ''}
          onChange={(e) =>
            onLiquidityChange(e.target.value ? Number(e.target.value) : null)
          }
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
          data-testid="liquidity-select"
        >
          <option value="">All</option>
          <option value="1">Tier 1 (High)</option>
          <option value="2">Tier 2 (Medium)</option>
          <option value="3">Tier 3 (Low)</option>
        </select>
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
