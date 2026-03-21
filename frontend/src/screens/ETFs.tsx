import { useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts'
import { useTopETFs, useSectorRankings, useCountryRankings } from '@/api/hooks/useRankings'
import { COUNTRY_FLAGS, COUNTRY_NAMES, SECTOR_DISPLAY_NAMES } from '@/data/countryData'
import { formatPercent } from '@/utils/format'
import PeriodSelector from '@/components/common/PeriodSelector'
import ActionFilter from '@/components/common/ActionFilter'
import ViewToggle from '@/components/common/ViewToggle'
import type { Period } from '@/components/common/PeriodSelector'
import type { ViewMode } from '@/components/common/ViewToggle'
import type { RankingItem, Action } from '@/types/rs'
import { actionLabel, watchSubLabel, volumeLabel } from '@/types/rs'

const ACTION_CONFIG: Record<Action, { bg: string; text: string; border: string; dot: string; description: string }> = {
  BUY:            { bg: 'bg-emerald-50',  text: 'text-emerald-700',  border: 'border-emerald-200', dot: '#059669', description: 'Rising, outperforming, and strengthening' },
  HOLD:           { bg: 'bg-amber-50',    text: 'text-amber-700',    border: 'border-amber-200',   dot: '#d97706', description: 'Outperforming but momentum fading' },
  WATCH_EMERGING: { bg: 'bg-blue-50',     text: 'text-blue-700',     border: 'border-blue-200',    dot: '#2563eb', description: 'Rising and strengthening, but still lagging peers' },
  WATCH_RELATIVE: { bg: 'bg-sky-50',      text: 'text-sky-700',      border: 'border-sky-200',     dot: '#0284c7', description: 'Outperforming despite price decline' },
  WATCH_EARLY:    { bg: 'bg-indigo-50',   text: 'text-indigo-700',   border: 'border-indigo-200',  dot: '#4f46e5', description: 'Earliest reversal — momentum just turned positive' },
  AVOID:          { bg: 'bg-orange-50',    text: 'text-orange-700',   border: 'border-orange-200',  dot: '#ea580c', description: 'Rising but lagging with fading momentum' },
  SELL:           { bg: 'bg-red-50',       text: 'text-red-700',      border: 'border-red-200',     dot: '#dc2626', description: 'Falling with weakening relative strength' },
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

function ETFActionBoard({ items }: { items: RankingItem[] }): JSX.Element {
  const grouped = new Map<Action, RankingItem[]>()
  for (const item of items) {
    const list = grouped.get(item.action) ?? []
    list.push(item)
    grouped.set(item.action, list)
  }
  for (const [, list] of grouped) list.sort((a, b) => b.rs_score - a.rs_score)

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
              <span className={`text-xs ${cfg.text} opacity-70`}>{list.length} ETFs</span>
            </div>
            <p className={`text-xs ${cfg.text} opacity-60 mb-3`}>{cfg.description}</p>

            <div className="space-y-1.5">
              {list.map((item) => (
                <div
                  key={item.instrument_id}
                  className="flex items-center justify-between bg-white/70 rounded-lg px-3 py-2"
                >
                  <div className="truncate">
                    <span className="text-sm font-medium text-slate-800">{item.instrument_id}</span>
                    <span className="text-xs text-slate-400 ml-1.5 truncate">{item.name}</span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0 ml-2">
                    <span className="font-mono text-xs font-semibold text-slate-700">{item.rs_score.toFixed(1)}</span>
                    <ReturnBadge value={item.absolute_return} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function ETFScatter({ items }: { items: RankingItem[] }): JSX.Element {
  const data = items.map((item) => ({
    x: item.rs_score - 50,
    y: item.rs_momentum ?? 0,
    name: item.name,
    id: item.instrument_id,
    action: item.action,
    item,
  }))

  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ payload: typeof data[0] }> }) => {
    if (!active || !payload?.length) return null
    const d = payload[0].payload
    return (
      <div className="bg-white border border-slate-200 rounded-lg shadow-lg p-3 text-xs">
        <div className="font-semibold text-slate-900 mb-1">{d.name}</div>
        <div className="text-slate-400 mb-1">{d.id}</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
          <span className="text-slate-500">RS Score</span>
          <span className="font-mono">{(d.x + 50).toFixed(1)}</span>
          <span className="text-slate-500">Momentum</span>
          <span className="font-mono">{d.y.toFixed(1)}</span>
          <span className="text-slate-500">Abs Return</span>
          <span className="font-mono">{d.item.absolute_return != null ? `${d.item.absolute_return.toFixed(1)}%` : '--'}</span>
          <span className="text-slate-500">Volume</span>
          <span>{volumeLabel(d.item.volume_signal)}</span>
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
      <h3 className="text-sm font-semibold text-slate-700 mb-3">ETF Relative Strength ({items.length} ETFs tracked)</h3>
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
          <Scatter data={data} fill="#0d9488">
            {data.map((entry, idx) => (
              <circle
                key={idx}
                r={6}
                fill={ACTION_CONFIG[entry.action]?.dot ?? '#94a3b8'}
                fillOpacity={0.7}
                stroke={ACTION_CONFIG[entry.action]?.dot ?? '#94a3b8'}
                strokeWidth={1}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>

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

function ETFTable({ items }: { items: RankingItem[] }): JSX.Element {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
        <span className="text-sm font-semibold text-slate-700">ETF Rankings</span>
        <span className="text-xs text-slate-400 ml-2">({items.length} ETFs)</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">ETF</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">Sector</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">Action</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">RS %</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">Abs %</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">Momentum</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">Volume</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">Reason</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const etfSector = SECTOR_DISPLAY_NAMES[item.sector ?? ''] ?? item.sector ?? '--'
              const rsColor = (item.rs_score - 50) > 0 ? 'text-emerald-600' : 'text-red-600'
              const momColor = (item.rs_momentum ?? 0) > 0 ? 'text-emerald-600' : 'text-red-600'

              return (
                <tr key={item.instrument_id} className="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="text-sm font-semibold text-slate-900">{item.instrument_id}</div>
                    <div className="text-xs text-slate-400 truncate max-w-[200px]">{item.name}</div>
                  </td>
                  <td className="px-3 py-3 text-center text-xs text-slate-600">{etfSector}</td>
                  <td className="px-3 py-3 text-center"><ActionBadge action={item.action} /></td>
                  <td className={`px-3 py-3 text-center font-mono text-sm ${rsColor}`}>{item.rs_score.toFixed(1)}</td>
                  <td className="px-3 py-3 text-center"><ReturnBadge value={item.absolute_return} /></td>
                  <td className={`px-3 py-3 text-center font-mono text-sm ${momColor}`}>{(item.rs_momentum ?? 0).toFixed(1)}</td>
                  <td className="px-3 py-3 text-center text-xs text-slate-500">{volumeLabel(item.volume_signal)}</td>
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

export default function ETFs(): JSX.Element {
  const { countryCode, sectorSlug } = useParams<{ countryCode: string; sectorSlug: string }>()
  const code = countryCode ?? ''
  const sector = sectorSlug ?? ''

  const [period, setPeriod] = useState<Period>('3m')
  const [actionFilter, setActionFilter] = useState<Action | null>(null)
  const [view, setView] = useState<ViewMode>('table')

  const { data: etfs, isLoading, error } = useTopETFs(undefined, code, sector, 200, period)
  const { data: sectors } = useSectorRankings(code, null, null, period)
  const { data: countries } = useCountryRankings(null, null, period)

  const country = countries?.find((c) => c.country === code)
  const sectorInfo = sectors?.find((s) => s.sector === sector || s.instrument_id === sector)
  const flag = COUNTRY_FLAGS[code] ?? ''
  const countryName = COUNTRY_NAMES[code] ?? code
  const sectorName = SECTOR_DISPLAY_NAMES[sector] ?? sector

  const filtered = useMemo(() => {
    if (!etfs) return []
    if (!actionFilter) return etfs
    return etfs.filter((e) => e.action === actionFilter)
  }, [etfs, actionFilter])

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-slate-500 mb-4">
        <Link to="/compass" className="hover:text-teal-600 transition-colors">Countries</Link>
        <span>/</span>
        <Link to={`/compass/country/${code}`} className="hover:text-teal-600 transition-colors">{flag} {countryName}</Link>
        <span>/</span>
        <span className="text-slate-900 font-medium">{sectorName}</span>
      </nav>

      {/* Sector Summary Card */}
      {sectorInfo && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 mb-4">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-xl font-bold text-slate-900">{sectorName}</h1>
              <p className="text-sm text-slate-500">{flag} {countryName} — sector ETFs ranked by relative strength</p>
            </div>
            <div className="flex items-center gap-6 flex-wrap">
              <ActionBadge action={sectorInfo.action} />
              <div className="text-center">
                <div className="text-2xl font-bold font-mono text-slate-900">{sectorInfo.rs_score.toFixed(1)}</div>
                <div className="text-xs text-slate-400">RS Score</div>
              </div>
              <div className="flex gap-4 text-center">
                {([
                  { label: '3M', value: sectorInfo.return_3m },
                  { label: '6M', value: sectorInfo.return_6m },
                  { label: '12M', value: sectorInfo.return_12m },
                ] as const).map(({ label, value }) => (
                  <div key={label}>
                    <div className={`text-sm font-mono font-semibold ${
                      (value ?? 0) > 0 ? 'text-emerald-600' : (value ?? 0) < 0 ? 'text-red-600' : 'text-slate-500'
                    }`}>
                      {value != null ? formatPercent(value) : '--'}
                    </div>
                    <div className="text-xs text-slate-400">{label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          {sectorInfo.action_reason && (
            <p className="text-xs text-slate-400 italic mt-2">{sectorInfo.action_reason}</p>
          )}
        </div>
      )}

      {/* Fallback header */}
      {!sectorInfo && country && (
        <div className="mb-4">
          <h1 className="text-xl font-bold text-slate-900">{sectorName} ETFs — {flag} {countryName}</h1>
        </div>
      )}

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
      {isLoading && <div className="flex items-center justify-center h-48 text-slate-400">Loading ETF data...</div>}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">Failed to load ETF rankings.</div>
      )}

      {filtered.length > 0 && (
        <div className="space-y-6">
          {/* Board or Table */}
          {view === 'kanban' ? (
            <ETFActionBoard items={filtered} />
          ) : (
            <ETFTable items={filtered} />
          )}

          {/* Scatter Chart */}
          <ETFScatter items={filtered} />
        </div>
      )}

      {etfs && etfs.length === 0 && !isLoading && (
        <div className="text-center py-16 text-slate-400">No ETFs found for {sectorName} in {countryName}.</div>
      )}
    </div>
  )
}
