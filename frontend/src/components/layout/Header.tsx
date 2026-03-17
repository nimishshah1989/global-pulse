import RegimeBanner from '@/components/common/RegimeBanner'
import Breadcrumb from '@/components/layout/Breadcrumb'
import { useRegimeStore } from '@/store/regimeStore'
import { useBenchmarkStore } from '@/store/benchmarkStore'

const BENCHMARK_OPTIONS = [
  { value: 'ACWI', label: 'MSCI ACWI' },
  { value: 'GLD', label: 'Gold' },
  { value: 'SHY', label: 'USD Cash' },
  { value: 'EEM', label: 'EM' },
  { value: 'VEA', label: 'Developed ex-US' },
]

export default function Header(): JSX.Element {
  const regime = useRegimeStore((state) => state.regime)
  const benchmark = useBenchmarkStore((state) => state.benchmark)
  const setBenchmark = useBenchmarkStore((state) => state.setBenchmark)

  return (
    <header className="space-y-3 border-b border-slate-200 bg-white px-6 py-4">
      <div className="flex items-center justify-between">
        <Breadcrumb />
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm">
            <label htmlFor="benchmark-select" className="text-slate-500 font-medium">
              Benchmark:
            </label>
            <select
              id="benchmark-select"
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
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
            Data fresh
          </div>
        </div>
      </div>
      <RegimeBanner regime={regime} />
    </header>
  )
}
