import { useState, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import type { SignalType, Opportunity } from '@/types/opportunities'
import SignalTypeBadge from '@/components/common/SignalTypeBadge'
import AlignmentCard from '@/components/common/AlignmentCard'
import LoadingSkeleton from '@/components/common/LoadingSkeleton'
import ErrorAlert from '@/components/common/ErrorAlert'
import { formatDate } from '@/utils/format'
import { useOpportunities, useMultiLevelAlignments } from '@/api/hooks/useOpportunities'
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
  const navigate = useNavigate()
  const [signalTypeFilter, setSignalTypeFilter] = useState<SignalType | ''>('')
  const [convictionMin, setConvictionMin] = useState(0)
  const [levelFilter, setLevelFilter] = useState('')

  const opportunityFilters = useMemo(() => {
    const filters: Record<string, unknown> = {}
    if (signalTypeFilter) filters.signal_type = signalTypeFilter
    if (convictionMin > 0) filters.min_conviction = convictionMin
    if (levelFilter) filters.hierarchy_level = Number(levelFilter)
    return filters.signal_type || filters.min_conviction || filters.hierarchy_level
      ? filters as { signal_type?: SignalType; min_conviction?: number; hierarchy_level?: number }
      : undefined
  }, [signalTypeFilter, convictionMin, levelFilter])

  const { data: opportunitiesData, isLoading: oppsLoading, error: oppsError, refetch: refetchOpps } = useOpportunities(opportunityFilters)
  const { data: alignmentsData, isLoading: alignmentsLoading } = useMultiLevelAlignments()

  const opportunities = opportunitiesData ?? MOCK_OPPORTUNITIES
  const alignments = alignmentsData ?? MOCK_ALIGNMENTS

  const nonAlignmentSignals = useMemo(() => {
    return opportunities.filter((opp) => {
      if (opp.signal_type === 'multi_level_alignment') return false
      if (signalTypeFilter && opp.signal_type !== signalTypeFilter) return false
      if (opp.conviction_score < convictionMin) return false
      return true
    })
  }, [opportunities, signalTypeFilter, convictionMin])

  const handleSignalClick = useCallback((opp: Opportunity): void => {
    // Navigate based on signal metadata or instrument
    const meta = opp.metadata
    if (meta && typeof meta.country === 'string' && typeof meta.sector === 'string') {
      const sectorSlug = (meta.sector as string).toLowerCase().replace(/[\s.]+/g, '-')
      navigate(`/compass/country/${meta.country}/sector/${sectorSlug}`)
    } else if (meta && typeof meta.country === 'string') {
      navigate(`/compass/country/${meta.country}`)
    }
  }, [navigate])

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

      {oppsError && (
        <ErrorAlert
          message={oppsError instanceof Error ? oppsError.message : 'Unknown error'}
          onRetry={() => void refetchOpps()}
        />
      )}

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
            value={levelFilter}
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
      {showAlignments && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-slate-900">
            Multi-Level Alignments
          </h2>
          {alignmentsLoading ? (
            <LoadingSkeleton type="card" rows={2} />
          ) : (
            alignments.length > 0 && (
              <div className="grid gap-4 md:grid-cols-2">
                {alignments.filter(
                  (a) => a.conviction_score >= convictionMin,
                ).map((alignment) => (
                  <AlignmentCard key={alignment.id} opportunity={alignment} onClick={() => handleSignalClick(alignment)} />
                ))}
              </div>
            )
          )}
        </div>
      )}

      {/* Signal feed table */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-slate-900">Signal Feed</h2>
        {oppsLoading ? (
          <LoadingSkeleton type="table" rows={8} />
        ) : (
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
                    onClick={() => handleSignalClick(opp)}
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
        )}
      </div>
    </div>
  )
}
