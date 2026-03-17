import type { BasketPerformance } from '@/types/baskets'
import { formatPercent } from '@/utils/format'

interface PerformanceStatsProps {
  performance: BasketPerformance
}

interface StatCardProps {
  label: string
  value: string
  colorClass: string
}

function StatCard({ label, value, colorClass }: StatCardProps): JSX.Element {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4" data-testid="stat-card">
      <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </div>
      <div className={`mt-1 font-mono text-xl font-bold ${colorClass}`}>{value}</div>
    </div>
  )
}

export default function PerformanceStats({ performance }: PerformanceStatsProps): JSX.Element {
  const returnColor = performance.cumulative_return >= 0 ? 'text-emerald-600' : 'text-red-600'
  const drawdownColor = 'text-red-600'
  const sharpeColor =
    performance.sharpe_ratio !== null && performance.sharpe_ratio >= 1.0
      ? 'text-emerald-600'
      : 'text-slate-900'
  const outperfColor =
    performance.pct_weeks_outperforming >= 50 ? 'text-emerald-600' : 'text-red-600'

  return (
    <div className="grid grid-cols-2 gap-3" data-testid="performance-stats">
      <StatCard
        label="Cumulative Return"
        value={formatPercent(performance.cumulative_return)}
        colorClass={returnColor}
      />
      <StatCard
        label="CAGR"
        value={performance.cagr !== null ? formatPercent(performance.cagr) : 'N/A'}
        colorClass={performance.cagr !== null && performance.cagr >= 0 ? 'text-emerald-600' : 'text-slate-500'}
      />
      <StatCard
        label="Max Drawdown"
        value={formatPercent(performance.max_drawdown)}
        colorClass={drawdownColor}
      />
      <StatCard
        label="Sharpe Ratio"
        value={performance.sharpe_ratio !== null ? performance.sharpe_ratio.toFixed(2) : 'N/A'}
        colorClass={sharpeColor}
      />
      <StatCard
        label="% Weeks Outperforming"
        value={`${performance.pct_weeks_outperforming.toFixed(1)}%`}
        colorClass={outperfColor}
      />
    </div>
  )
}
