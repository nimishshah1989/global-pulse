import { useNavigate } from 'react-router-dom'
import { useCountryRankings } from '@/api/hooks/useRankings'
import { useRegime } from '@/api/hooks/useRegime'
import { COUNTRY_FLAGS, COUNTRY_NAMES } from '@/data/countryData'
import { formatPercent } from '@/utils/format'
import type { RankingItem, Action } from '@/types/rs'

const ACTION_COLORS: Record<Action, string> = {
  BUY: 'bg-emerald-100 text-emerald-700',
  ACCUMULATE: 'bg-teal-100 text-teal-700',
  HOLD_DIVERGENCE: 'bg-yellow-100 text-yellow-700',
  HOLD_FADING: 'bg-yellow-100 text-yellow-700',
  WATCH: 'bg-blue-100 text-blue-700',
  REDUCE: 'bg-orange-100 text-orange-700',
  SELL: 'bg-red-100 text-red-700',
  AVOID: 'bg-slate-200 text-slate-600',
}

const ACTION_LABELS: Record<Action, string> = {
  BUY: 'Buy',
  ACCUMULATE: 'Accumulate',
  HOLD_DIVERGENCE: 'Hold',
  HOLD_FADING: 'Hold',
  WATCH: 'Watch',
  REDUCE: 'Reduce',
  SELL: 'Sell',
  AVOID: 'Avoid',
}

function ReturnCell({ value }: { value: number | null | undefined }): JSX.Element {
  if (value == null) return <td className="px-3 py-3 text-center text-slate-300 font-mono text-sm">--</td>
  const color = value > 0 ? 'text-emerald-600' : value < 0 ? 'text-red-600' : 'text-slate-500'
  return <td className={`px-3 py-3 text-center font-mono text-sm ${color}`}>{formatPercent(value)}</td>
}

function ActionBadge({ action }: { action: Action }): JSX.Element {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${ACTION_COLORS[action]}`}>
      {ACTION_LABELS[action]}
    </span>
  )
}

function CountryRow({ item, onClick }: { item: RankingItem; onClick: () => void }): JSX.Element {
  const code = item.country ?? ''
  const flag = COUNTRY_FLAGS[code] ?? ''
  const name = COUNTRY_NAMES[code] ?? item.name

  return (
    <tr
      className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
      onClick={onClick}
    >
      <td className="px-4 py-3 font-medium text-slate-900">
        <div className="flex items-center gap-2">
          <span className="text-lg">{flag}</span>
          <div>
            <div className="text-sm font-semibold">{name}</div>
            <div className="text-xs text-slate-400">{item.name}</div>
          </div>
        </div>
      </td>
      <td className="px-3 py-3 text-center"><ActionBadge action={item.action} /></td>
      <td className="px-3 py-3 text-center font-mono text-sm font-semibold text-slate-700">
        {item.rs_score?.toFixed(1)}
      </td>
      <td className="px-3 py-3 text-center text-xs">
        <span className={item.price_trend === 'OUTPERFORMING' ? 'text-emerald-600' : 'text-red-500'}>
          {item.price_trend === 'OUTPERFORMING' ? 'Outperforming' : 'Underperforming'}
        </span>
      </td>
      <td className="px-3 py-3 text-center text-xs">
        <span className={item.momentum_trend === 'ACCELERATING' ? 'text-emerald-600' : 'text-orange-500'}>
          {item.momentum_trend === 'ACCELERATING' ? 'Accelerating' : 'Decelerating'}
        </span>
      </td>
      <ReturnCell value={item.return_1m} />
      <ReturnCell value={item.return_3m} />
      <ReturnCell value={item.return_6m} />
      <ReturnCell value={item.return_12m} />
      <ReturnCell value={item.excess_3m} />
      <ReturnCell value={item.excess_6m} />
    </tr>
  )
}

export default function Countries(): JSX.Element {
  const navigate = useNavigate()
  const { data: countries, isLoading, error } = useCountryRankings()
  const { data: regimeData } = useRegime()

  const regime = regimeData?.regime ?? 'RISK_ON'

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Global Pulse</h1>
          <p className="text-sm text-slate-500 mt-1">Country relative strength vs ACWI benchmark</p>
        </div>
        <div className={`px-4 py-2 rounded-lg text-sm font-semibold ${
          regime === 'RISK_ON' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
        }`}>
          {regime === 'RISK_ON' ? 'Risk On' : 'Risk Off'}
        </div>
      </div>

      {/* Loading / Error States */}
      {isLoading && (
        <div className="flex items-center justify-center h-64 text-slate-400">Loading country data...</div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
          Failed to load country rankings. Please check API connection.
        </div>
      )}

      {/* Table */}
      {countries && countries.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Country</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Action</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">RS Score</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Trend</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Momentum</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">1M</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">3M</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">6M</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">12M</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Excess 3M</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Excess 6M</th>
              </tr>
            </thead>
            <tbody>
              {countries.map((item) => (
                <CountryRow
                  key={item.instrument_id}
                  item={item}
                  onClick={() => navigate(`/compass/country/${item.country}`)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {countries && countries.length === 0 && !isLoading && (
        <div className="text-center py-16 text-slate-400">No country data available.</div>
      )}
    </div>
  )
}
