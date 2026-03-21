import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer, Cell } from 'recharts'
import { useCountryRankings } from '@/api/hooks/useRankings'
import { useRegime } from '@/api/hooks/useRegime'
import { COUNTRY_FLAGS, COUNTRY_NAMES } from '@/data/countryData'
import { formatPercent } from '@/utils/format'
import PeriodSelector from '@/components/common/PeriodSelector'
import ActionFilter from '@/components/common/ActionFilter'
import ViewToggle from '@/components/common/ViewToggle'
import type { Period } from '@/components/common/PeriodSelector'
import type { ViewMode } from '@/components/common/ViewToggle'
import type { RankingItem, Action, MarketRegime } from '@/types/rs'
import { actionLabel, watchSubLabel, volumeLabel, regimeLabel } from '@/types/rs'

// Action card colors — matching MarketPulse exactly
const ACTION_CONFIG: Record<Action, { bg: string; text: string; border: string; dot: string; description: string }> = {
  BUY:            { bg: 'bg-emerald-50',  text: 'text-emerald-700',  border: 'border-emerald-200', dot: '#059669', description: 'Rising, outperforming, and strengthening' },
  HOLD:           { bg: 'bg-amber-50',    text: 'text-amber-700',    border: 'border-amber-200',   dot: '#d97706', description: 'Outperforming but momentum fading' },
  WATCH_EMERGING: { bg: 'bg-blue-50',     text: 'text-blue-700',     border: 'border-blue-200',    dot: '#2563eb', description: 'Rising and strengthening, but still lagging peers' },
  WATCH_RELATIVE: { bg: 'bg-sky-50',      text: 'text-sky-700',      border: 'border-sky-200',     dot: '#0284c7', description: 'Outperforming despite price decline' },
  WATCH_EARLY:    { bg: 'bg-indigo-50',   text: 'text-indigo-700',   border: 'border-indigo-200',  dot: '#4f46e5', description: 'Earliest reversal — momentum just turned positive' },
  AVOID:          { bg: 'bg-orange-50',    text: 'text-orange-700',   border: 'border-orange-200',  dot: '#ea580c', description: 'Rising but lagging with fading momentum' },
  SELL:           { bg: 'bg-red-50',       text: 'text-red-700',      border: 'border-red-200',     dot: '#dc2626', description: 'Falling with weakening relative strength' },
}

const REGIME_CONFIG: Record<MarketRegime, { bg: string; text: string }> = {
  BULL:       { bg: 'bg-emerald-100', text: 'text-emerald-700' },
  CAUTIOUS:   { bg: 'bg-amber-100',   text: 'text-amber-700' },
  CORRECTION: { bg: 'bg-orange-100',  text: 'text-orange-700' },
  BEAR:       { bg: 'bg-red-100',     text: 'text-red-700' },
}

function ActionBadge({ action }: { action: Action }): JSX.Element {
  const cfg = ACTION_CONFIG[action]
  const sub = watchSubLabel(action)
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${cfg.bg} ${cfg.text}`}>
      {actionLabel(action)}{sub ? ` (${sub})` : ''}
    </span>
  )
}

function ReturnBadge({ value }: { value: number | null }): JSX.Element {
  if (value == null) return <span className="text-slate-300 font-mono text-xs">--</span>
  const color = value > 0 ? 'text-emerald-600' : value < 0 ? 'text-red-600' : 'text-slate-500'
  return <span className={`font-mono text-xs ${color}`}>{formatPercent(value)}</span>
}

// Action Board — group countries by action, display as cards
function ActionBoard({ items, onItemClick }: { items: RankingItem[]; onItemClick: (item: RankingItem) => void }): JSX.Element {
  const grouped = new Map<Action, RankingItem[]>()
  for (const item of items) {
    const list = grouped.get(item.action) ?? []
    list.push(item)
    grouped.set(item.action, list)
  }

  // Sort within each group by RS score desc
  for (const [, list] of grouped) {
    list.sort((a, b) => b.rs_score - a.rs_score)
  }

  const actionOrder: Action[] = ['BUY', 'HOLD', 'WATCH_EMERGING', 'WATCH_RELATIVE', 'WATCH_EARLY', 'AVOID', 'SELL']

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
      {actionOrder.map((action) => {
        const list = grouped.get(action)
        if (!list || list.length === 0) return null
        const cfg = ACTION_CONFIG[action]
        const sub = watchSubLabel(action)

        return (
          <div key={action} className={`rounded-xl border ${cfg.border} ${cfg.bg} p-4`}>
            <div className="flex items-center justify-between mb-2">
              <h3 className={`text-sm font-semibold ${cfg.text}`}>
                {actionLabel(action)}{sub ? ` — ${sub}` : ''}
              </h3>
              <span className={`text-xs ${cfg.text} opacity-70`}>{list.length} {list.length === 1 ? 'country' : 'countries'}</span>
            </div>
            <p className={`text-xs ${cfg.text} opacity-60 mb-3`}>{cfg.description}</p>

            <div className="space-y-1.5">
              {list.map((item) => {
                const code = item.country ?? ''
                const flag = COUNTRY_FLAGS[code] ?? ''
                const name = COUNTRY_NAMES[code] ?? item.name

                return (
                  <button
                    key={item.instrument_id}
                    onClick={() => onItemClick(item)}
                    className="w-full flex items-center justify-between bg-white/70 hover:bg-white rounded-lg px-3 py-2 transition-colors group"
                    title={item.action_reason ?? undefined}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-sm">{flag}</span>
                      <span className="text-sm font-medium text-slate-800 truncate">{name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs font-semibold text-slate-700">{item.rs_score.toFixed(1)}</span>
                      <ReturnBadge value={item.absolute_return} />
                      {item.volume_signal && (
                        <span className="text-xs text-slate-400">{volumeLabel(item.volume_signal)}</span>
                      )}
                      <svg className="w-4 h-4 text-slate-300 group-hover:text-slate-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// RRG Scatter Chart for countries
function CountryScatter({ items, onItemClick }: { items: RankingItem[]; onItemClick: (item: RankingItem) => void }): JSX.Element {
  const data = items.map((item) => ({
    x: item.rs_score - 50,
    y: item.rs_momentum ?? 0,
    name: COUNTRY_NAMES[item.country ?? ''] ?? item.name,
    flag: COUNTRY_FLAGS[item.country ?? ''] ?? '',
    action: item.action,
    item,
  }))

  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ payload: typeof data[0] }> }) => {
    if (!active || !payload?.length) return null
    const d = payload[0].payload
    return (
      <div className="bg-white border border-slate-200 rounded-lg shadow-lg p-3 text-xs">
        <div className="font-semibold text-slate-900 mb-1">{d.flag} {d.name}</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
          <span className="text-slate-500">RS Score</span>
          <span className="font-mono">{(d.x + 50).toFixed(1)}</span>
          <span className="text-slate-500">Momentum</span>
          <span className="font-mono">{d.y.toFixed(1)}</span>
          <span className="text-slate-500">Action</span>
          <span>{actionLabel(d.action)}</span>
        </div>
        {d.item.action_reason && (
          <div className="mt-1.5 text-slate-400 italic">{d.item.action_reason}</div>
        )}
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <h3 className="text-sm font-semibold text-slate-700 mb-3">Country Relative Strength Scatter</h3>
      <ResponsiveContainer width="100%" height={400}>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            type="number" dataKey="x" name="RS Score"
            tickFormatter={(v: number) => `${v > 0 ? '+' : ''}${v.toFixed(0)}`}
            label={{ value: 'RS Score (vs 50)', position: 'bottom', offset: -5, style: { fontSize: 11, fill: '#94a3b8' } }}
          />
          <YAxis
            type="number" dataKey="y" name="Momentum"
            tickFormatter={(v: number) => `${v > 0 ? '+' : ''}${v.toFixed(0)}`}
            label={{ value: 'Momentum', angle: -90, position: 'insideLeft', style: { fontSize: 11, fill: '#94a3b8' } }}
          />
          <ReferenceLine x={0} stroke="#94a3b8" strokeDasharray="3 3" />
          <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="3 3" />
          <Tooltip content={<CustomTooltip />} />
          <Scatter
            data={data}
            onClick={(_: unknown, __: unknown, event: unknown) => {
              const idx = (event as { index?: number })?.index
              if (idx != null && data[idx]) onItemClick(data[idx].item)
            }}
            cursor="pointer"
          >
            {data.map((entry, idx) => {
              const color = ACTION_CONFIG[entry.action]?.dot ?? '#94a3b8'
              const absRet = Math.abs(entry.item.absolute_return ?? 0)
              const r = Math.max(6, Math.min(16, 6 + absRet * 0.4))
              return (
                <Cell
                  key={idx}
                  fill={color}
                  fillOpacity={0.7}
                  stroke={color}
                  strokeWidth={2}
                  r={r}
                />
              )
            })}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mt-2 justify-center">
        {(['BUY', 'HOLD', 'WATCH_EMERGING', 'AVOID', 'SELL'] as Action[]).map((a) => (
          <div key={a} className="flex items-center gap-1.5 text-xs text-slate-500">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: ACTION_CONFIG[a].dot }} />
            {actionLabel(a)}
          </div>
        ))}
      </div>
    </div>
  )
}

// Country Ranking Table
function CountryTable({ items, onItemClick }: { items: RankingItem[]; onItemClick: (item: RankingItem) => void }): JSX.Element {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
        <span className="text-sm font-semibold text-slate-700">Country Rankings</span>
        <span className="text-xs text-slate-400 ml-2">({items.length} countries)</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Country</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">Action</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">RS %</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">Abs %</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">Momentum</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">Volume</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">1M</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">3M</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">6M</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">Reason</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const code = item.country ?? ''
              const rsColor = (item.rs_score - 50) > 0 ? 'text-emerald-600' : 'text-red-600'
              const momColor = (item.rs_momentum ?? 0) > 0 ? 'text-emerald-600' : 'text-red-600'

              return (
                <tr
                  key={item.instrument_id}
                  className="border-b border-slate-50 hover:bg-slate-50 cursor-pointer transition-colors"
                  onClick={() => onItemClick(item)}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="text-sm">{COUNTRY_FLAGS[code] ?? ''}</span>
                      <span className="text-sm font-semibold text-slate-900">{COUNTRY_NAMES[code] ?? item.name}</span>
                    </div>
                  </td>
                  <td className="px-3 py-3 text-center"><ActionBadge action={item.action} /></td>
                  <td className={`px-3 py-3 text-center font-mono text-sm ${rsColor}`}>{item.rs_score.toFixed(1)}</td>
                  <td className="px-3 py-3 text-center"><ReturnBadge value={item.absolute_return} /></td>
                  <td className={`px-3 py-3 text-center font-mono text-sm ${momColor}`}>{(item.rs_momentum ?? 0).toFixed(1)}</td>
                  <td className="px-3 py-3 text-center text-xs text-slate-500">{volumeLabel(item.volume_signal)}</td>
                  <td className="px-3 py-3 text-center"><ReturnBadge value={item.return_1m} /></td>
                  <td className="px-3 py-3 text-center"><ReturnBadge value={item.return_3m} /></td>
                  <td className="px-3 py-3 text-center"><ReturnBadge value={item.return_6m} /></td>
                  <td className="px-3 py-3 text-xs text-slate-400 italic max-w-[200px] truncate">{item.action_reason ?? '--'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function Countries(): JSX.Element {
  const navigate = useNavigate()
  const [period, setPeriod] = useState<Period>('3m')
  const [actionFilter, setActionFilter] = useState<Action | null>(null)
  const [view, setView] = useState<ViewMode>('kanban')

  const { data: countries, isLoading, error } = useCountryRankings(null, null, period)
  const { data: regimeData } = useRegime()

  const regime = (regimeData?.regime ?? 'BULL') as MarketRegime
  const rCfg = REGIME_CONFIG[regime] ?? REGIME_CONFIG.BULL

  const filtered = useMemo(() => {
    if (!countries) return []
    if (!actionFilter) return countries
    return countries.filter((c) => c.action === actionFilter)
  }, [countries, actionFilter])

  const handleClick = (item: RankingItem) => {
    navigate(`/compass/country/${item.country}`)
  }

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Global Pulse</h1>
          <p className="text-sm text-slate-500 mt-1">Country relative strength vs <span className="font-semibold text-teal-600">ACWI</span> benchmark</p>
        </div>
        <div className={`px-4 py-2 rounded-lg text-sm font-semibold ${rCfg.bg} ${rCfg.text}`}>
          {regimeLabel(regime)}
        </div>
      </div>

      {/* Controls bar */}
      <div className="flex items-center justify-between gap-4 mb-6 flex-wrap">
        <div className="flex items-center gap-3 flex-wrap">
          <PeriodSelector value={period} onChange={setPeriod} />
          <div className="w-px h-6 bg-slate-200" />
          <ActionFilter value={actionFilter} onChange={setActionFilter} />
        </div>
        <ViewToggle value={view} onChange={setView} />
      </div>

      {/* Loading / Error */}
      {isLoading && (
        <div className="flex items-center justify-center h-64 text-slate-400">Loading country data...</div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
          Failed to load country rankings. Please check API connection.
        </div>
      )}

      {filtered.length > 0 && (
        <div className="space-y-6">
          {/* Action Board or Table based on view toggle */}
          {view === 'kanban' ? (
            <ActionBoard items={filtered} onItemClick={handleClick} />
          ) : (
            <CountryTable items={filtered} onItemClick={handleClick} />
          )}

          {/* Scatter Chart */}
          <CountryScatter items={filtered} onItemClick={handleClick} />
        </div>
      )}

      {countries && countries.length === 0 && !isLoading && (
        <div className="text-center py-16 text-slate-400">No country data available.</div>
      )}
    </div>
  )
}
