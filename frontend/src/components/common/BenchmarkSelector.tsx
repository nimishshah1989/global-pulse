import { useBenchmarkStore } from '@/store/benchmarkStore'

const BENCHMARK_OPTIONS = [
  { value: 'ACWI', label: 'MSCI ACWI' },
  { value: 'GLD', label: 'Gold' },
  { value: 'SHY', label: 'USD Cash' },
  { value: 'EEM', label: 'Emerging Markets' },
  { value: 'VEA', label: 'Developed ex-US' },
] as const

export default function BenchmarkSelector(): JSX.Element {
  const benchmark = useBenchmarkStore((state) => state.benchmark)
  const setBenchmark = useBenchmarkStore((state) => state.setBenchmark)

  return (
    <div className="flex items-center gap-2">
      <label
        htmlFor="benchmark-selector"
        className="text-sm font-medium text-slate-500"
      >
        Benchmark:
      </label>
      <select
        id="benchmark-selector"
        value={benchmark}
        onChange={(e) => setBenchmark(e.target.value)}
        className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
      >
        {BENCHMARK_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}
