import { useState, useCallback, useMemo, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import RRGScatter from '@/components/charts/RRGScatter'
import RSRankingTable from '@/components/tables/RSRankingTable'
import RSLineChart from '@/components/charts/RSLineChart'
import Breadcrumb from '@/components/layout/Breadcrumb'
import RegimeBanner from '@/components/common/RegimeBanner'
import DateNavigator from '@/components/common/DateNavigator'
import ActionBadge from '@/components/common/QuadrantBadge'
import WeightBadge from '@/components/common/WeightBadge'
import LoadingSkeleton from '@/components/common/LoadingSkeleton'
import ErrorAlert from '@/components/common/ErrorAlert'
import { useSectorRankings } from '@/api/hooks/useRankings'
import { useSectorRRG } from '@/api/hooks/useRRG'
import { useRegime } from '@/api/hooks/useRegime'
import { useInstrumentPrices, computeRSLineFromPrices } from '@/api/hooks/useInstrument'
import { COUNTRY_NAMES, COUNTRY_BENCHMARK_MAP } from '@/data/mockCountryData'
import type { RankingItem, Action, RRGDataPoint } from '@/types/rs'

type ActionFilterGroup = 'ALL' | 'BUY' | 'HOLD' | 'SELL' | 'WATCH' | 'ACCUMULATE' | 'REDUCE' | 'AVOID'

const FILTER_GROUPS: ActionFilterGroup[] = ['ALL', 'BUY', 'HOLD', 'SELL', 'WATCH', 'ACCUMULATE', 'REDUCE', 'AVOID']

const HOLD_ACTIONS: Action[] = ['HOLD_DIVERGENCE', 'HOLD_FADING']

function matchesFilter(action: Action, filter: ActionFilterGroup): boolean {
  if (filter === 'ALL') return true
  if (filter === 'HOLD') return HOLD_ACTIONS.includes(action)
  return action === filter
}

const FILTER_COLORS: Record<ActionFilterGroup, { active: string; inactive: string }> = {
  ALL: { active: 'bg-teal-600 text-white', inactive: 'bg-white text-slate-700 border-slate-200' },
  BUY: { active: 'bg-emerald-600 text-white', inactive: 'bg-white text-emerald-700 border-emerald-200' },
  HOLD: { active: 'bg-yellow-600 text-white', inactive: 'bg-white text-yellow-700 border-yellow-200' },
  SELL: { active: 'bg-red-600 text-white', inactive: 'bg-white text-red-700 border-red-200' },
  WATCH: { active: 'bg-blue-600 text-white', inactive: 'bg-white text-blue-700 border-blue-200' },
  ACCUMULATE: { active: 'bg-teal-600 text-white', inactive: 'bg-white text-teal-700 border-teal-200' },
  REDUCE: { active: 'bg-orange-600 text-white', inactive: 'bg-white text-orange-700 border-orange-200' },
  AVOID: { active: 'bg-slate-600 text-white', inactive: 'bg-white text-slate-600 border-slate-200' },
}

function getTrendArrow(trend: string | null): string {
  if (trend === 'OUTPERFORMING' || trend === 'ACCELERATING') return '\u25B2'
  if (trend === 'UNDERPERFORMING' || trend === 'DECELERATING') return '\u25BC'
  return '\u2014'
}

function getTrendColor(trend: string | null): string {
  if (trend === 'OUTPERFORMING' || trend === 'ACCELERATING') return 'text-emerald-600'
  if (trend === 'UNDERPERFORMING' || trend === 'DECELERATING') return 'text-red-600'
  return 'text-slate-400'
}

export default function CountryDeepDive(): JSX.Element {
  const { countryCode } = useParams<{ countryCode: string }>()
  const code = countryCode ?? 'US'
  const navigate = useNavigate()

  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const { data: sectorData, isLoading: sectorsLoading, error: sectorsError, refetch: refetchSectors } = useSectorRankings(code, selectedDate)
  const { data: rrgApiData, isLoading: rrgLoading } = useSectorRRG(code)
  const { data: regimeData } = useRegime()

  const countryName = COUNTRY_NAMES[code] ?? code
  const sectors: RankingItem[] = Array.isArray(sectorData) ? sectorData : []
  const rrgData: RRGDataPoint[] = rrgApiData ?? []

  const [selectedSectorId, setSelectedSectorId] = useState<string>('')
  const [selectedSectorName, setSelectedSectorName] = useState<string>('')
  const [actionFilter, setActionFilter] = useState<ActionFilterGroup>('ALL')

  const benchmarkId = COUNTRY_BENCHMARK_MAP[code] ?? 'SPX'
  const { data: sectorPrices } = useInstrumentPrices(selectedSectorId, 500)
  const { data: benchmarkPrices } = useInstrumentPrices(benchmarkId, 500)

  const rsLineData = useMemo(() => {
    if (sectorPrices && benchmarkPrices && sectorPrices.length > 50 && benchmarkPrices.length > 50) {
      return computeRSLineFromPrices(sectorPrices, benchmarkPrices)
    }
    return []
  }, [sectorPrices, benchmarkPrices])

  const filteredSectors = useMemo(() => {
    return sectors.filter((s) => matchesFilter(s.action, actionFilter))
  }, [sectors, actionFilter])

  const filterCounts = useMemo(() => {
    const counts: Record<ActionFilterGroup, number> = {
      ALL: sectors.length, BUY: 0, HOLD: 0, SELL: 0, WATCH: 0, ACCUMULATE: 0, REDUCE: 0, AVOID: 0,
    }
    sectors.forEach((s) => {
      if (HOLD_ACTIONS.includes(s.action)) counts.HOLD++
      else if (s.action in counts) counts[s.action as ActionFilterGroup]++
    })
    return counts
  }, [sectors])

  const handleSectorSelect = useCallback((item: RankingItem) => {
    setSelectedSectorId(item.instrument_id)
    setSelectedSectorName(item.name)
  }, [])

  const handleRRGPointClick = useCallback((id: string) => {
    const sector = sectors.find((s) => s.instrument_id === id)
    if (sector) {
      setSelectedSectorId(sector.instrument_id)
      setSelectedSectorName(sector.name)
    }
  }, [sectors])

  const displaySectorName = selectedSectorName || sectors[0]?.name || 'Select a sector'

  useEffect(() => {
    if (!selectedSectorId && sectors.length > 0) {
      setSelectedSectorId(sectors[0].instrument_id)
      setSelectedSectorName(sectors[0].name)
    }
  }, [sectors, selectedSectorId])

  return (
    <div className="space-y-6">
      <div>
        <Breadcrumb />
        <div className="mt-2 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              {countryName} — Sector Rotation
            </h1>
            <p className="text-sm text-slate-500">Which sectors are leading within this market?</p>
          </div>
          <DateNavigator selectedDate={selectedDate} onDateChange={setSelectedDate} />
        </div>
      </div>

      {regimeData && <RegimeBanner regime={regimeData.regime} />}

      {sectorsError && (
        <ErrorAlert
          message={sectorsError instanceof Error ? sectorsError.message : 'Unknown error'}
          onRetry={() => void refetchSectors()}
        />
      )}

      {/* Sector Cards */}
      {!sectorsLoading && sectors.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">
            Sector Allocation View — {countryName}
          </h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {sectors.map((sector) => (
              <SectorCard
                key={sector.instrument_id}
                sector={sector}
                isSelected={selectedSectorId === sector.instrument_id}
                onClick={() => handleSectorSelect(sector)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Action filter */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Filter:</span>
        {FILTER_GROUPS.map((f) => {
          const count = filterCounts[f]
          const isActive = actionFilter === f
          const colors = FILTER_COLORS[f]
          return (
            <button
              key={f}
              onClick={() => setActionFilter(f)}
              className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${isActive ? colors.active : colors.inactive}`}
            >
              {f === 'ALL' ? 'All' : f.charAt(0) + f.slice(1).toLowerCase()} ({count})
            </button>
          )
        })}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">Sector Rankings</h2>
          {sectorsLoading ? (
            <LoadingSkeleton type="table" rows={8} />
          ) : (
            <RSRankingTable data={filteredSectors} onRowClick={handleSectorSelect} showSector />
          )}
        </div>
        <div className="lg:col-span-3">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">Relative Rotation Graph</h2>
          {rrgLoading ? (
            <LoadingSkeleton type="chart" />
          ) : (
            <RRGScatter data={rrgData} width={580} height={450} onPointClick={handleRRGPointClick} />
          )}
        </div>
      </div>

      <div>
        <RSLineChart data={rsLineData} title={`RS Line — ${displaySectorName} vs ${countryName} Index`} />
        <div className="mt-2 flex items-center justify-between">
          <p className="text-xs text-slate-400">
            Click a sector card or table row to view its RS line.
          </p>
          {selectedSectorId && (
            <button
              onClick={() => {
                const sector = sectors.find((s) => s.instrument_id === selectedSectorId)
                const slug = sector?.sector ?? selectedSectorId
                navigate(`/compass/country/${code}/sector/${slug}`)
              }}
              className="rounded-lg bg-primary-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-primary-700 transition-colors"
            >
              View Stocks in {displaySectorName} &rarr;
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

/* ---------- Sector Card Sub-component ---------- */

function SectorCard({ sector, isSelected, onClick }: {
  sector: RankingItem
  isSelected: boolean
  onClick: () => void
}): JSX.Element {
  const score = sector.rs_score ?? 0
  const momentumPct = sector.rs_momentum_pct

  return (
    <div
      onClick={onClick}
      className={`cursor-pointer rounded-lg border p-3 transition-all hover:shadow-md ${
        isSelected
          ? 'border-teal-400 bg-teal-50/50 ring-1 ring-teal-200'
          : 'border-slate-200 hover:border-slate-300'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-slate-900">{sector.name}</p>
          <div className="mt-1 flex items-center gap-2">
            <span className="font-mono text-lg font-bold text-slate-800">
              {score.toFixed(1)}
            </span>
            <span className={`text-sm ${getTrendColor(sector.price_trend)}`}>
              {getTrendArrow(sector.price_trend)}
            </span>
          </div>
        </div>
        <div className="ml-2 flex flex-col items-end gap-1">
          <WeightBadge action={sector.action} />
          <ActionBadge action={sector.action} />
        </div>
      </div>
      <div className="mt-2 flex gap-3 text-[10px] text-slate-500">
        <span>
          Mom: <span className={`font-mono font-medium ${getTrendColor(sector.momentum_trend)}`}>
            {momentumPct !== null && momentumPct !== undefined ? `${momentumPct > 0 ? '+' : ''}${momentumPct.toFixed(1)}%` : '--'}
          </span>
        </span>
        <span>
          Vol: <span className={`font-mono font-medium ${
            sector.volume_character === 'ACCUMULATION' ? 'text-emerald-600'
              : sector.volume_character === 'DISTRIBUTION' ? 'text-red-500'
              : 'text-slate-500'
          }`}>
            {sector.volume_character ?? '--'}
          </span>
        </span>
      </div>
    </div>
  )
}
