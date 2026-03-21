import { useState, useMemo } from 'react'
import { useTopETFs } from '@/api/hooks/useRankings'
import { COUNTRY_FLAGS, COUNTRY_NAMES, SECTOR_DISPLAY_NAMES } from '@/data/countryData'
import { formatPercent } from '@/utils/format'
import PeriodSelector from '@/components/common/PeriodSelector'
import ActionFilter from '@/components/common/ActionFilter'
import type { Period } from '@/components/common/PeriodSelector'
import type { Action } from '@/types/rs'
import { actionLabel, watchSubLabel, volumeLabel } from '@/types/rs'

const COUNTRIES = ['US', 'UK', 'JP', 'HK', 'IN', 'KR', 'CN', 'TW', 'AU', 'BR', 'CA', 'DE', 'FR'] as const
const SECTORS = [
  'technology', 'financials', 'healthcare', 'energy', 'industrials',
  'materials', 'consumer_discretionary', 'consumer_staples',
  'utilities', 'real_estate', 'communication_services',
] as const

const ACTION_CONFIG: Record<Action, { bg: string; text: string }> = {
  BUY:            { bg: 'bg-emerald-50', text: 'text-emerald-700' },
  HOLD:           { bg: 'bg-amber-50',   text: 'text-amber-700' },
  WATCH_EMERGING: { bg: 'bg-blue-50',    text: 'text-blue-700' },
  WATCH_RELATIVE: { bg: 'bg-sky-50',     text: 'text-sky-700' },
  WATCH_EARLY:    { bg: 'bg-indigo-50',  text: 'text-indigo-700' },
  AVOID:          { bg: 'bg-orange-50',   text: 'text-orange-700' },
  SELL:           { bg: 'bg-red-50',      text: 'text-red-700' },
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

export default function ETFScanner(): JSX.Element {
  const [period, setPeriod] = useState<Period>('3m')
  const [actionFilter, setActionFilter] = useState<Action | null>(null)
  const [countryFilter, setCountryFilter] = useState<string>('')
  const [sectorFilter, setSectorFilter] = useState<string>('')

  const { data: etfs, isLoading, error } = useTopETFs(
    actionFilter ?? undefined,
    countryFilter || undefined,
    sectorFilter || undefined,
    500,
    period,
  )

  const filtered = useMemo(() => {
    if (!etfs) return []
    let items = etfs
    if (actionFilter) {
      items = items.filter((e) => e.action === actionFilter)
    }
    if (countryFilter) {
      items = items.filter((e) => e.country === countryFilter)
    }
    if (sectorFilter) {
      items = items.filter((e) => e.sector === sectorFilter)
    }
    return items
  }, [etfs, actionFilter, countryFilter, sectorFilter])

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">ETF Scanner</h1>
          <p className="text-sm text-slate-500 mt-1">All ETFs across all countries, ranked by relative strength</p>
        </div>
        <PeriodSelector value={period} onChange={setPeriod} />
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 mb-4 flex-wrap">
        <ActionFilter value={actionFilter} onChange={setActionFilter} />
      </div>
      <div className="flex items-center gap-3 mb-6">
        <select
          value={countryFilter}
          onChange={(e) => setCountryFilter(e.target.value)}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 focus:outline-none focus:ring-2 focus:ring-teal-500"
        >
          <option value="">All Countries</option>
          {COUNTRIES.map((code) => (
            <option key={code} value={code}>{COUNTRY_FLAGS[code]} {COUNTRY_NAMES[code]}</option>
          ))}
        </select>
        <select
          value={sectorFilter}
          onChange={(e) => setSectorFilter(e.target.value)}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 focus:outline-none focus:ring-2 focus:ring-teal-500"
        >
          <option value="">All Sectors</option>
          {SECTORS.map((s) => (
            <option key={s} value={s}>{SECTOR_DISPLAY_NAMES[s] ?? s}</option>
          ))}
        </select>
        {filtered.length > 0 && (
          <span className="text-xs text-slate-400">{filtered.length} ETFs</span>
        )}
      </div>

      {/* Loading / Error */}
      {isLoading && (
        <div className="flex items-center justify-center h-64 text-slate-400">Loading ETF data...</div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
          Failed to load ETF rankings. Please check API connection.
        </div>
      )}

      {/* Table */}
      {filtered.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">ETF</th>
                  <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">Country</th>
                  <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">Sector</th>
                  <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">Action</th>
                  <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">RS %</th>
                  <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">Abs %</th>
                  <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">Momentum</th>
                  <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">Volume</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => {
                  const code = item.country ?? ''
                  const sectorName = SECTOR_DISPLAY_NAMES[item.sector ?? ''] ?? item.sector ?? '--'
                  const rsColor = (item.rs_score - 50) > 0 ? 'text-emerald-600' : 'text-red-600'
                  const momColor = (item.rs_momentum ?? 0) > 0 ? 'text-emerald-600' : 'text-red-600'

                  return (
                    <tr key={item.instrument_id} className="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="text-sm font-semibold text-slate-900">{item.instrument_id}</div>
                        <div className="text-xs text-slate-400 truncate max-w-[200px]">{item.name}</div>
                      </td>
                      <td className="px-3 py-3 text-center text-xs text-slate-600">
                        {COUNTRY_FLAGS[code]} {code}
                      </td>
                      <td className="px-3 py-3 text-center text-xs text-slate-600">{sectorName}</td>
                      <td className="px-3 py-3 text-center"><ActionBadge action={item.action} /></td>
                      <td className={`px-3 py-3 text-center font-mono text-sm ${rsColor}`}>{item.rs_score.toFixed(1)}</td>
                      <td className="px-3 py-3 text-center"><ReturnBadge value={item.absolute_return} /></td>
                      <td className={`px-3 py-3 text-center font-mono text-sm ${momColor}`}>{(item.rs_momentum ?? 0).toFixed(1)}</td>
                      <td className="px-3 py-3 text-center text-xs text-slate-500">{volumeLabel(item.volume_signal)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!isLoading && filtered.length === 0 && !error && (
        <div className="text-center py-16 text-slate-400">No ETFs match the current filters.</div>
      )}
    </div>
  )
}
