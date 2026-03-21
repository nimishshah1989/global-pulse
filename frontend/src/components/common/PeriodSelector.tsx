const PERIODS = ['1m', '3m', '6m', '12m'] as const

export type Period = (typeof PERIODS)[number]

interface PeriodSelectorProps {
  value: Period
  onChange: (period: Period) => void
}

const PERIOD_LABELS: Record<Period, string> = {
  '1m': '1M',
  '3m': '3M',
  '6m': '6M',
  '12m': '12M',
}

export default function PeriodSelector({ value, onChange }: PeriodSelectorProps): JSX.Element {
  return (
    <div className="flex items-center gap-1">
      {PERIODS.map((p) => (
        <button
          key={p}
          onClick={() => onChange(p)}
          className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
            value === p
              ? 'bg-teal-600 text-white'
              : 'bg-slate-100 text-slate-500 hover:bg-slate-200 hover:text-slate-700'
          }`}
        >
          {PERIOD_LABELS[p]}
        </button>
      ))}
    </div>
  )
}
