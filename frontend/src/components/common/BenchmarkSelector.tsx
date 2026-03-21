const BENCHMARKS = [
  { value: '', label: 'Default' },
  { value: 'ACWI', label: 'ACWI' },
  { value: 'SPX', label: 'S&P 500' },
  { value: 'NSEI', label: 'NIFTY 50' },
  { value: 'GLD', label: 'Gold' },
  { value: 'SHY', label: 'USD Cash' },
  { value: 'EEM', label: 'EM' },
  { value: 'VEA', label: 'Dev ex-US' },
] as const

export type Benchmark = (typeof BENCHMARKS)[number]['value']

interface BenchmarkSelectorProps {
  value: Benchmark
  onChange: (benchmark: Benchmark) => void
}

export default function BenchmarkSelector({ value, onChange }: BenchmarkSelectorProps): JSX.Element {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-xs font-medium text-slate-400 mr-0.5">vs</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as Benchmark)}
        className="text-xs font-semibold bg-slate-100 text-slate-700 rounded-full px-3 py-1 border-0 cursor-pointer hover:bg-slate-200 transition-colors focus:ring-2 focus:ring-teal-500 focus:outline-none appearance-none pr-6"
        style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 8px center' }}
      >
        {BENCHMARKS.map((b) => (
          <option key={b.value} value={b.value}>
            {b.label}
          </option>
        ))}
      </select>
    </div>
  )
}
