import { useState, useMemo } from 'react'
import type { SignalType } from '@/types/opportunities'
import SignalTypeBadge from '@/components/common/SignalTypeBadge'
import AlignmentCard from '@/components/common/AlignmentCard'
import { formatDate } from '@/utils/format'
import { MOCK_ALIGNMENTS, MOCK_OPPORTUNITIES } from '@/data/mockOpportunityData'

const SIGNAL_TYPE_OPTIONS: { value: SignalType | ''; label: string }[] = [
  { value: '', label: 'All Signals' },
  { value: 'multi_level_alignment', label: 'Multi-Level Alignment' },
  { value: 'quadrant_entry_leading', label: 'Entry: Leading' },
  { value: 'quadrant_entry_improving', label: 'Entry: Improving' },
  { value: 'volume_breakout', label: 'Volume Breakout' },
  { value: 'bearish_divergence', label: 'Bearish Divergence' },
  { value: 'bullish_divergence', label: 'Bullish Divergence' },
  { value: 'regime_change', label: 'Regime Change' },
  { value: 'extension_alert', label: 'Extension Alert' },
]

const LEVEL_OPTIONS = [
  { value: '', label: 'All Levels' },
  { value: '1', label: 'Country' },
  { value: '2', label: 'Sector' },
  { value: '3', label: 'Stock' },
]

export default function OpportunityScanner(): JSX.Element {
  const [signalTypeFilter, setSignalTypeFilter] = useState<SignalType | ''>('')
  const [convictionMin, setConvictionMin] = useState(0)
  const [_levelFilter, setLevelFilter] = useState('')

  const nonAlignmentSignals = useMemo(() => {
    return MOCK_OPPORTUNITIES.filter((opp) => {
      if (opp.signal_type === 'multi_level_alignment') return false
      if (signalTypeFilter && opp.signal_type !== signalTypeFilter) return false
      if (opp.conviction_score < convictionMin) return false
      return true
    })
  }, [signalTypeFilter, convictionMin])

  const showAlignments =
    signalTypeFilter === '' || signalTypeFilter === 'multi_level_alignment'

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          🎯 Opportunity Scanner
        </h1>
        <p className="text-sm text-slate-500">
          What should I be paying attention to today?
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 rounded-xl border border-slate-200 bg-white px-5 py-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Signal Type
          </span>
          <select
            value={signalTypeFilter}
            onChange={(e) => setSignalTypeFilter(e.target.value as SignalType | '')}
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
          >
            {SIGNAL_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Level
          </span>
          <select
            value={_levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
          >
            {LEVEL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Min Conviction
          </span>
          <input
            type="range"
            min={0}
            max={100}
            value={convictionMin}
            onChange={(e) => setConvictionMin(Number(e.target.value))}
            className="h-1.5 w-24 cursor-pointer appearance-none rounded-full bg-slate-200 accent-teal-600"
          />
          <span className="font-mono text-sm font-medium text-slate-700">{convictionMin}</span>
        </div>
      </div>

      {/* Multi-level alignment cards */}
      {showAlignments && MOCK_ALIGNMENTS.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-slate-900">
            Multi-Level Alignments
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            {MOCK_ALIGNMENTS.filter(
              (a) => a.conviction_score >= convictionMin,
            ).map((alignment) => (
              <AlignmentCard key={alignment.id} opportunity={alignment} />
            ))}
          </div>
        </div>
      )}

      {/* Signal feed table */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-slate-900">Signal Feed</h2>
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Date
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Instrument
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Signal Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Conviction
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Description
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {nonAlignmentSignals.map((opp) => (
                <tr
                  key={opp.id}
                  className="cursor-pointer transition-colors hover:bg-slate-50"
                >
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-slate-600">
                    {formatDate(opp.date)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 font-medium text-slate-900">
                    {opp.instrument_name}
                  </td>
                  <td className="px-4 py-3">
                    <SignalTypeBadge signalType={opp.signal_type} />
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`font-mono font-semibold ${
                        opp.conviction_score >= 70
                          ? 'text-emerald-600'
                          : opp.conviction_score >= 50
                            ? 'text-amber-600'
                            : 'text-slate-500'
                      }`}
                    >
                      {opp.conviction_score}
                    </span>
                  </td>
                  <td className="max-w-xs truncate px-4 py-3 text-slate-600">
                    {opp.description}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
