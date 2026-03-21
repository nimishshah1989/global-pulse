import { useModelPortfolio } from '@/api/hooks/usePortfolio'
import { formatPercent, formatDate } from '@/utils/format'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import type { Action } from '@/types/rs'
import { actionLabel } from '@/types/rs'

const ACTION_BADGE_COLORS: Record<Action, { bg: string; text: string }> = {
  BUY:            { bg: 'bg-emerald-50', text: 'text-emerald-700' },
  HOLD:           { bg: 'bg-amber-50',   text: 'text-amber-700' },
  WATCH_EMERGING: { bg: 'bg-blue-50',    text: 'text-blue-700' },
  WATCH_RELATIVE: { bg: 'bg-sky-50',     text: 'text-sky-700' },
  WATCH_EARLY:    { bg: 'bg-indigo-50',  text: 'text-indigo-700' },
  AVOID:          { bg: 'bg-orange-50',   text: 'text-orange-700' },
  SELL:           { bg: 'bg-red-50',      text: 'text-red-700' },
}

interface PortfolioPosition {
  instrument_id: string
  name: string
  weight: number
  pnl_percent: number | null
  action: Action
  stop_price: number | null
}

interface PortfolioTrade {
  date: string
  instrument_id: string
  side: 'ENTRY' | 'EXIT'
  reason: string
}

interface NavPoint {
  date: string
  portfolio_nav: number
  benchmark_nav: number
}

interface PortfolioData {
  summary: {
    nav: number
    cumulative_return: number
    sharpe: number | null
    max_drawdown: number | null
    positions_count: number
  }
  nav_history: NavPoint[]
  positions: PortfolioPosition[]
  recent_trades: PortfolioTrade[]
}

function StatCard({ label, value, color }: { label: string; value: string; color?: string }): JSX.Element {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <div className="text-xs text-slate-400 mb-1">{label}</div>
      <div className={`text-xl font-bold font-mono ${color ?? 'text-slate-900'}`}>{value}</div>
    </div>
  )
}

export default function ModelPortfolio(): JSX.Element {
  const { data, isLoading, error } = useModelPortfolio('etf_only')

  const portfolio = data as PortfolioData | undefined

  if (isLoading) {
    return (
      <div className="p-6 max-w-[1400px] mx-auto">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Model Portfolio</h1>
        <div className="flex items-center justify-center h-64 text-slate-400">Loading portfolio data...</div>
      </div>
    )
  }

  if (error || !portfolio) {
    return (
      <div className="p-6 max-w-[1400px] mx-auto">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Model Portfolio</h1>
        <p className="text-sm text-slate-500 mb-6">RS-driven ETF portfolio tracking</p>
        <div className="bg-slate-50 rounded-xl border border-slate-200 p-12 text-center">
          <div className="text-4xl mb-4">&#128188;</div>
          <h2 className="text-lg font-semibold text-slate-700 mb-2">Model Portfolio coming soon</h2>
          <p className="text-sm text-slate-500 max-w-md mx-auto">
            Building positions from BUY signals across global ETFs. The portfolio engine will track entries, exits, and NAV performance against benchmark.
          </p>
        </div>
      </div>
    )
  }

  const { summary, nav_history, positions, recent_trades } = portfolio
  const returnColor = summary.cumulative_return >= 0 ? 'text-emerald-600' : 'text-red-600'
  const ddColor = (summary.max_drawdown ?? 0) < -10 ? 'text-red-600' : 'text-slate-900'

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Model Portfolio</h1>
        <p className="text-sm text-slate-500 mt-1">RS-driven ETF portfolio tracking</p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="NAV" value={summary.nav.toFixed(2)} />
        <StatCard label="Cumulative Return" value={formatPercent(summary.cumulative_return)} color={returnColor} />
        <StatCard label="Sharpe Ratio" value={summary.sharpe != null ? summary.sharpe.toFixed(2) : '--'} />
        <StatCard label="Max Drawdown" value={summary.max_drawdown != null ? formatPercent(summary.max_drawdown) : '--'} color={ddColor} />
      </div>

      {/* NAV Chart */}
      {nav_history.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-4 mb-6">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">NAV vs Benchmark</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={nav_history}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="date"
                tickFormatter={(d: string) => formatDate(d)}
                tick={{ fontSize: 10, fill: '#94a3b8' }}
              />
              <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} />
              <Tooltip
                labelFormatter={(d) => formatDate(String(d))}
                formatter={(v, name) => [Number(v).toFixed(2), String(name) === 'portfolio_nav' ? 'Portfolio' : 'Benchmark']}
              />
              <Legend formatter={(v: string) => v === 'portfolio_nav' ? 'Portfolio' : 'Benchmark'} />
              <Line type="monotone" dataKey="portfolio_nav" stroke="#0d9488" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="benchmark_nav" stroke="#94a3b8" strokeWidth={1.5} dot={false} strokeDasharray="4 4" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Positions */}
      {positions.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden mb-6">
          <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
            <span className="text-sm font-semibold text-slate-700">Current Positions</span>
            <span className="text-xs text-slate-400 ml-2">({positions.length})</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Instrument</th>
                  <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase">Weight</th>
                  <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase">P&L</th>
                  <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase">Action</th>
                  <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase">Stop</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos) => {
                  const pnlColor = (pos.pnl_percent ?? 0) >= 0 ? 'text-emerald-600' : 'text-red-600'
                  const aCfg = ACTION_BADGE_COLORS[pos.action]
                  return (
                    <tr key={pos.instrument_id} className="border-b border-slate-50 hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <div className="text-sm font-semibold text-slate-900">{pos.instrument_id}</div>
                        <div className="text-xs text-slate-400">{pos.name}</div>
                      </td>
                      <td className="px-3 py-3 text-center font-mono text-sm text-slate-700">{(pos.weight * 100).toFixed(1)}%</td>
                      <td className={`px-3 py-3 text-center font-mono text-sm ${pnlColor}`}>
                        {pos.pnl_percent != null ? formatPercent(pos.pnl_percent) : '--'}
                      </td>
                      <td className="px-3 py-3 text-center">
                        <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${aCfg.bg} ${aCfg.text}`}>
                          {actionLabel(pos.action)}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-center font-mono text-xs text-slate-500">
                        {pos.stop_price != null ? `$${pos.stop_price.toFixed(2)}` : '--'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Recent Trades */}
      {recent_trades.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
            <span className="text-sm font-semibold text-slate-700">Recent Trades</span>
          </div>
          <div className="divide-y divide-slate-50">
            {recent_trades.map((trade, idx) => (
              <div key={idx} className="px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                    trade.side === 'ENTRY' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
                  }`}>
                    {trade.side}
                  </span>
                  <span className="text-sm font-medium text-slate-900">{trade.instrument_id}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-slate-400">{trade.reason}</span>
                  <span className="text-xs text-slate-300">{formatDate(trade.date)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
