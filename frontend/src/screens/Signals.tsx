import { useState, useMemo } from 'react'
import { useOpportunities } from '@/api/hooks/usePortfolio'
import { COUNTRY_FLAGS, COUNTRY_NAMES, SECTOR_DISPLAY_NAMES } from '@/data/countryData'
import { formatDate } from '@/utils/format'

interface Opportunity {
  id: string
  instrument_id: string
  name: string
  country: string | null
  sector: string | null
  date: string
  signal_type: string
  conviction_score: number
  description: string
  metadata: Record<string, unknown> | null
}

const SIGNAL_TYPES = [
  'quadrant_entry_leading',
  'quadrant_entry_improving',
  'volume_breakout',
  'multi_level_alignment',
  'bearish_divergence',
  'bullish_divergence',
  'regime_change',
  'extension_alert',
] as const

const SIGNAL_LABELS: Record<string, { label: string; color: string }> = {
  quadrant_entry_leading:   { label: 'Entered Leading',     color: 'bg-emerald-50 text-emerald-700' },
  quadrant_entry_improving: { label: 'Entered Improving',   color: 'bg-blue-50 text-blue-700' },
  volume_breakout:          { label: 'Volume Breakout',     color: 'bg-teal-50 text-teal-700' },
  multi_level_alignment:    { label: 'Multi-Level Aligned', color: 'bg-purple-50 text-purple-700' },
  bearish_divergence:       { label: 'Bearish Divergence',  color: 'bg-red-50 text-red-700' },
  bullish_divergence:       { label: 'Bullish Divergence',  color: 'bg-emerald-50 text-emerald-700' },
  regime_change:            { label: 'Regime Change',       color: 'bg-amber-50 text-amber-700' },
  extension_alert:          { label: 'Extension Alert',     color: 'bg-orange-50 text-orange-700' },
}

function SignalBadge({ type }: { type: string }): JSX.Element {
  const cfg = SIGNAL_LABELS[type] ?? { label: type, color: 'bg-slate-50 text-slate-700' }
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${cfg.color}`}>
      {cfg.label}
    </span>
  )
}

function ConvictionBar({ score }: { score: number }): JSX.Element {
  const width = Math.min(Math.max(score, 0), 100)
  const color = score >= 80 ? 'bg-emerald-500' : score >= 60 ? 'bg-teal-500' : score >= 40 ? 'bg-amber-500' : 'bg-slate-400'
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${width}%` }} />
      </div>
      <span className="font-mono text-xs text-slate-600">{score.toFixed(0)}</span>
    </div>
  )
}

// Multi-level alignment signals get prominent card display
function AlignmentCard({ signal }: { signal: Opportunity }): JSX.Element {
  const flag = COUNTRY_FLAGS[signal.country ?? ''] ?? ''
  const countryName = COUNTRY_NAMES[signal.country ?? ''] ?? signal.country ?? ''
  const sectorName = SECTOR_DISPLAY_NAMES[signal.sector ?? ''] ?? signal.sector ?? ''

  return (
    <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <SignalBadge type={signal.signal_type} />
        <ConvictionBar score={signal.conviction_score} />
      </div>
      <div className="text-sm font-semibold text-slate-900 mb-1">{signal.instrument_id} — {signal.name}</div>
      <div className="text-xs text-purple-700">
        {flag} {countryName} {sectorName ? `\u203A ${sectorName}` : ''} {'\u203A'} {signal.instrument_id}
      </div>
      <p className="text-xs text-slate-500 mt-2">{signal.description}</p>
      <div className="text-xs text-slate-300 mt-1">{formatDate(signal.date)}</div>
    </div>
  )
}

export default function Signals(): JSX.Element {
  const { data, isLoading, error } = useOpportunities()
  const [signalTypeFilter, setSignalTypeFilter] = useState<string>('')

  const opportunities = data as Opportunity[] | undefined

  const filtered = useMemo(() => {
    if (!opportunities) return []
    let items = opportunities
    if (signalTypeFilter) {
      items = items.filter((o) => o.signal_type === signalTypeFilter)
    }
    // Sort by conviction descending
    return [...items].sort((a, b) => b.conviction_score - a.conviction_score)
  }, [opportunities, signalTypeFilter])

  const multiLevel = filtered.filter((o) => o.signal_type === 'multi_level_alignment')
  const regular = filtered.filter((o) => o.signal_type !== 'multi_level_alignment')

  if (isLoading) {
    return (
      <div className="p-6 max-w-[1400px] mx-auto">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Signals</h1>
        <div className="flex items-center justify-center h-64 text-slate-400">Loading signals...</div>
      </div>
    )
  }

  if (error || !opportunities) {
    return (
      <div className="p-6 max-w-[1400px] mx-auto">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Signals</h1>
        <p className="text-sm text-slate-500 mb-6">Automated opportunity detection based on RS regime changes</p>
        <div className="bg-slate-50 rounded-xl border border-slate-200 p-12 text-center">
          <div className="text-4xl mb-4">&#127919;</div>
          <h2 className="text-lg font-semibold text-slate-700 mb-2">Opportunity signals coming soon</h2>
          <p className="text-sm text-slate-500 max-w-md mx-auto">
            The signal engine detects quadrant entries, volume breakouts, multi-level alignments, and divergences. Data will appear once the opportunity scanner is deployed.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Signals</h1>
          <p className="text-sm text-slate-500 mt-1">Automated opportunity detection — {filtered.length} signals</p>
        </div>
      </div>

      {/* Signal Type Filter */}
      <div className="flex items-center gap-1 flex-wrap mb-6">
        <button
          onClick={() => setSignalTypeFilter('')}
          className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
            !signalTypeFilter ? 'bg-slate-700 text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
          }`}
        >
          All
        </button>
        {SIGNAL_TYPES.map((st) => {
          const cfg = SIGNAL_LABELS[st]
          return (
            <button
              key={st}
              onClick={() => setSignalTypeFilter(signalTypeFilter === st ? '' : st)}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
                signalTypeFilter === st ? 'bg-teal-600 text-white' : `${cfg.color} hover:opacity-80`
              }`}
            >
              {cfg.label}
            </button>
          )
        })}
      </div>

      {/* Multi-Level Alignment Cards (prominent) */}
      {multiLevel.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Multi-Level Alignments (Highest Conviction)</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {multiLevel.map((signal) => (
              <AlignmentCard key={signal.id} signal={signal} />
            ))}
          </div>
        </div>
      )}

      {/* Regular Signals Table */}
      {regular.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
            <span className="text-sm font-semibold text-slate-700">Signal Feed</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Date</th>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Instrument</th>
                  <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase">Signal</th>
                  <th className="px-3 py-3 text-center text-xs font-semibold text-slate-400 uppercase">Conviction</th>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Description</th>
                </tr>
              </thead>
              <tbody>
                {regular.map((signal) => (
                  <tr key={signal.id} className="border-b border-slate-50 hover:bg-slate-50">
                    <td className="px-4 py-3 text-xs text-slate-500 whitespace-nowrap">{formatDate(signal.date)}</td>
                    <td className="px-3 py-3">
                      <div className="text-sm font-semibold text-slate-900">{signal.instrument_id}</div>
                      <div className="text-xs text-slate-400">{signal.name}</div>
                    </td>
                    <td className="px-3 py-3 text-center"><SignalBadge type={signal.signal_type} /></td>
                    <td className="px-3 py-3 text-center"><ConvictionBar score={signal.conviction_score} /></td>
                    <td className="px-3 py-3 text-xs text-slate-500 max-w-[300px] truncate">{signal.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {filtered.length === 0 && (
        <div className="text-center py-16 text-slate-400">No signals match the current filter.</div>
      )}
    </div>
  )
}
