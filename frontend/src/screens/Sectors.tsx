import { useState, useMemo } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer, Cell } from 'recharts'
import { useSectorRankings, useCountryRankings } from '@/api/hooks/useRankings'
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

function SectorActionBoard({ items, onItemClick }: { items: RankingItem[]; onItemClick: (item: RankingItem) => void }): JSX.Element {
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
              <span className={`text-xs ${cfg.text} opacity-70`}>{list.length}</span>
            </div>
            <p className={`text-xs ${cfg.text} opacity-60 mb-3`}>{cfg.description}</p>

            <div className="space-y-1.5">
              {list.map((item) => {
                const sectorName = SECTOR_DISPLAY_NAMES[item.sector ?? ''] ?? item.sector ?? item.name
                return (
                  <button
                    key={item.instrument_id}
                    onClick={() => onItemClick(item)}
                    className="w-full flex items-center justify-between bg-white/70 hover:bg-white rounded-lg px-3 py-2 transition-colors group"
                    title={item.action_reason ?? undefined}
                  >
                    <span className="text-sm font-medium text-slate-800 truncate">{sectorName}</span>
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs font-semibold text-slate-700">{item.rs_score.toFixed(1)}</span>
                      <ReturnBadge value={item.absolute_return} />
                      {item.volume_signal && (
                        <span className="text-xs text-slate-400">{volumeLabel(item.volume_signal)}</span>
                      )}
                      <svg className="w-4 h-4 text-slate-300 group-hover:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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

function SectorScatter({ items, onItemClick }: { items: RankingItem[]; onItemClick: (item: RankingItem) => void }): JSX.Element {
  const data = items.map((item) => ({
    x: item.rs_score - 50,
    y: item.rs_momentum ?? 0,
    name: SECTOR_DISPLAY_NAMES[item.sector ?? ''] ?? item.sector ?? item.name,
    action: item.action,
    item,
  }))

  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ payload: typeof data[0] }> }) => {
    if (!active || !payload?.length) return null
    const d = payload[0].payload
    return (
      <div className="bg-white border border-slate-200 rounded-lg shadow-lg p-3 text-xs">
        <div className="font-semibold text-slate-900 mb-1">{d.name}</div>
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
        <div className="mt-1.5 text-slate-300 text-[10px]">Click to drill into ETFs</div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <h3 className="text-sm font-semibold text-slate-700 mb-3">Sector Relative Strength ({items.length} sectors)</h3>
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

function SectorTable({ items, onItemClick }: { items: RankingItem[]; onItemClick: (item: RankingItem) => void }): JSX.Element {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
        <span className="text-sm font-semibold text-slate-700">Sector Rankings</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Sector</th>
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
              const sectorName = SECTOR_DISPLAY_NAMES[item.sector ?? ''] ?? item.sector ?? item.name
              const rsColor = (item.rs_score - 50) > 0 ? 'text-emerald-600' : 'text-red-600'
              const momColor = (item.rs_momentum ?? 0) > 0 ? 'text-emerald-600' : 'text-red-600'

              return (
                <tr
                  key={item.instrument_id}
                  className="border-b border-slate-50 hover:bg-slate-50 cursor-pointer transition-colors"
                  onClick={() => onItemClick(item)}
                >
                  <td className="px-4 py-3">
                    <div className="text-sm font-semibold text-slate-900">{sectorName}</div>
                    <div className="text-xs text-slate-400 font-mono">{item.instrument_id}</div>
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

export default function Sectors(): JSX.Element {
  const { countryCode } = useParams<{ countryCode: string }>()
  const navigate = useNavigate()
  const code = countryCode ?? ''

  const [period, setPeriod] = useState<Period>('3m')
  const [actionFilter, setActionFilter] = useState<Action | null>(null)
  const [view, setView] = useState<ViewMode>('kanban')

  const { data: sectors, isLoading, error } = useSectorRankings(code, null, null, period)
  const { data: countries } = useCountryRankings(null, null, period)

  const country = countries?.find((c) => c.country === code)
  const flag = COUNTRY_FLAGS[code] ?? ''
  const countryName = COUNTRY_NAMES[code] ?? code

  const filtered = useMemo(() => {
    if (!sectors) return []
    if (!actionFilter) return sectors
    return sectors.filter((s) => s.action === actionFilter)
  }, [sectors, actionFilter])

  const handleSectorClick = (item: RankingItem) => {
    navigate(`/compass/country/${code}/sector/${item.sector ?? item.instrument_id}`)
  }

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-slate-500 mb-4">
        <Link to="/compass" className="hover:text-teal-600 transition-colors">Countries</Link>
        <span>/</span>
        <span className="text-slate-900 font-medium">{flag} {countryName}</span>
      </nav>

      {/* Country Summary Card */}
      {country && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 mb-4">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-3">
              <span className="text-3xl">{flag}</span>
              <div>
                <h1 className="text-xl font-bold text-slate-900">{countryName}</h1>
                <p className="text-sm text-slate-500">Sectors vs <span className="font-semibold text-teal-600">{country.benchmark_id ?? countryName} index</span></p>
              </div>
            </div>
            <div className="flex items-center gap-6 flex-wrap">
              <ActionBadge action={country.action} />
              <div className="text-center">
                <div className="text-2xl font-bold font-mono text-slate-900">{country.rs_score.toFixed(1)}</div>
                <div className="text-xs text-slate-400">RS Score</div>
              </div>
              <div className="flex gap-4 text-center">
                {([
                  { label: '3M', value: country.return_3m },
                  { label: '6M', value: country.return_6m },
                  { label: '12M', value: country.return_12m },
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
          {country.action_reason && (
            <p className="text-xs text-slate-400 italic mt-2">{country.action_reason}</p>
          )}
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
      {isLoading && <div className="flex items-center justify-center h-48 text-slate-400">Loading sector data...</div>}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">Failed to load sector rankings.</div>
      )}

      {filtered.length > 0 && (
        <div className="space-y-6">
          {/* Action Board or Table */}
          {view === 'kanban' ? (
            <SectorActionBoard items={filtered} onItemClick={handleSectorClick} />
          ) : (
            <SectorTable items={filtered} onItemClick={handleSectorClick} />
          )}

          {/* Scatter Chart */}
          <SectorScatter items={filtered} onItemClick={handleSectorClick} />
        </div>
      )}

      {sectors && sectors.length === 0 && !isLoading && (
        <div className="text-center py-16 text-slate-400">No sector data available for {countryName}.</div>
      )}
    </div>
  )
}
