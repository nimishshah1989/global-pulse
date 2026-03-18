import { useState, useCallback, useMemo, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import RRGScatter from '@/components/charts/RRGScatter'
import RSRankingTable from '@/components/tables/RSRankingTable'
import RSLineChart from '@/components/charts/RSLineChart'
import Breadcrumb from '@/components/layout/Breadcrumb'
import RegimeBanner from '@/components/common/RegimeBanner'
import DateNavigator from '@/components/common/DateNavigator'
import QuadrantBadge from '@/components/common/QuadrantBadge'
import WeightBadge from '@/components/common/WeightBadge'
import LoadingSkeleton from '@/components/common/LoadingSkeleton'
import ErrorAlert from '@/components/common/ErrorAlert'
import { useSectorRankings } from '@/api/hooks/useRankings'
import { useSectorRRG } from '@/api/hooks/useRRG'
import { useRegime } from '@/api/hooks/useRegime'
import { useInstrumentPrices, computeRSLineFromPrices } from '@/api/hooks/useInstrument'
import { MOCK_SECTOR_DATA, getMockRRGData, getMockRSLineData } from '@/data/mockSectorData'
import { COUNTRY_NAMES, COUNTRY_BENCHMARK_MAP } from '@/data/mockCountryData'
import type { RankingItem, Quadrant } from '@/types/rs'

type QuadrantFilter = 'ALL' | Quadrant

export default function CountryDeepDive(): JSX.Element {
  const { countryCode } = useParams<{ countryCode: string }>()
  const navigate = useNavigate()
  const code = countryCode ?? 'US'

  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const { data: sectorData, isLoading: sectorsLoading, error: sectorsError, refetch: refetchSectors } = useSectorRankings(code, selectedDate)
  const { data: rrgApiData, isLoading: rrgLoading } = useSectorRRG(code)
  const { data: regimeData } = useRegime()

  const countryName = COUNTRY_NAMES[code] ?? code

  const mockSectors = MOCK_SECTOR_DATA[code] ?? MOCK_SECTOR_DATA['US'] ?? []
  const sectors = sectorData ?? mockSectors
  const rrgData = rrgApiData ?? getMockRRGData(code in MOCK_SECTOR_DATA ? code : 'US')

  const [selectedSectorId, setSelectedSectorId] = useState<string>('')
  const [selectedSectorName, setSelectedSectorName] = useState<string>('')
  const [quadrantFilter, setQuadrantFilter] = useState<QuadrantFilter>('ALL')

  // Fetch price data for selected sector and its benchmark
  const benchmarkId = COUNTRY_BENCHMARK_MAP[code] ?? 'SPX'
  const { data: sectorPrices } = useInstrumentPrices(selectedSectorId, 500)
  const { data: benchmarkPrices } = useInstrumentPrices(benchmarkId, 500)

  // Compute RS line from real prices, fall back to mock
  const rsLineData = useMemo(() => {
    if (sectorPrices && benchmarkPrices && sectorPrices.length > 50 && benchmarkPrices.length > 50) {
      return computeRSLineFromPrices(sectorPrices, benchmarkPrices)
    }
    return getMockRSLineData()
  }, [sectorPrices, benchmarkPrices])

  // Filter sectors by quadrant
  const filteredSectors = useMemo(() => {
    if (quadrantFilter === 'ALL') return sectors
    return sectors.filter((s) => s.quadrant === quadrantFilter)
  }, [sectors, quadrantFilter])

  // Quadrant counts for filter badges
  const quadrantCounts = useMemo(() => {
    const counts = { LEADING: 0, WEAKENING: 0, LAGGING: 0, IMPROVING: 0 }
    sectors.forEach((s) => {
      if (s.quadrant in counts) counts[s.quadrant as keyof typeof counts]++
    })
    return counts
  }, [sectors])

  const handleSectorSelect = useCallback(
    (item: RankingItem) => {
      setSelectedSectorId(item.instrument_id)
      setSelectedSectorName(item.name)
    },
    [],
  )

  const handleRRGPointClick = useCallback(
    (id: string) => {
      const sector = sectors.find((s) => s.instrument_id === id)
      if (sector?.sector) {
        navigate(`/compass/country/${code}/sector/${sector.sector}`)
      }
    },
    [navigate, code, sectors],
  )

  // Auto-select first sector if none selected
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

      {regimeData && (
        <RegimeBanner regime={regimeData.regime} />
      )}

      {sectorsError && (
        <ErrorAlert
          message={sectorsError instanceof Error ? sectorsError.message : 'Unknown error'}
          onRetry={() => void refetchSectors()}
        />
      )}

      {/* Sector Weight Recommendations Summary */}
      {!sectorsLoading && sectors.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">
            Sector Allocation View — {countryName}
          </h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {sectors.map((sector) => (
              <div
                key={sector.instrument_id}
                onClick={() => handleSectorSelect(sector)}
                className={`cursor-pointer rounded-lg border p-3 transition-all hover:shadow-md ${
                  selectedSectorId === sector.instrument_id
                    ? 'border-teal-400 bg-teal-50/50 ring-1 ring-teal-200'
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-slate-900">
                      {sector.name}
                    </p>
                    <div className="mt-1 flex items-center gap-2">
                      <span className="font-mono text-lg font-bold text-slate-800">
                        {sector.adjusted_rs_score.toFixed(1)}
                      </span>
                      <span
                        className={`font-mono text-xs font-medium ${
                          sector.rs_momentum > 0 ? 'text-emerald-600' : sector.rs_momentum < 0 ? 'text-red-600' : 'text-slate-500'
                        }`}
                      >
                        {sector.rs_momentum > 0 ? '+' : ''}
                        {sector.rs_momentum.toFixed(1)}
                      </span>
                    </div>
                  </div>
                  <div className="ml-2 flex flex-col items-end gap-1">
                    <WeightBadge
                      rsScore={sector.adjusted_rs_score}
                      rsMomentum={sector.rs_momentum}
                      quadrant={sector.quadrant}
                    />
                    <QuadrantBadge quadrant={sector.quadrant} />
                  </div>
                </div>
                <div className="mt-2 flex gap-3 text-[10px] text-slate-500">
                  <span>1M: <span className="font-mono font-medium">{sector.rs_pct_1m.toFixed(0)}</span></span>
                  <span>3M: <span className="font-mono font-medium">{sector.rs_pct_3m.toFixed(0)}</span></span>
                  <span>6M: <span className="font-mono font-medium">{sector.rs_pct_6m.toFixed(0)}</span></span>
                  <span>12M: <span className="font-mono font-medium">{sector.rs_pct_12m.toFixed(0)}</span></span>
                  <span>Vol: <span className={`font-mono font-medium ${sector.volume_ratio >= 1.0 ? 'text-emerald-600' : 'text-red-500'}`}>{sector.volume_ratio.toFixed(2)}</span></span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quadrant filter */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Filter:</span>
        {(['ALL', 'LEADING', 'WEAKENING', 'LAGGING', 'IMPROVING'] as const).map((q) => {
          const count = q === 'ALL' ? sectors.length : quadrantCounts[q]
          const isActive = quadrantFilter === q
          const colorMap: Record<string, string> = {
            ALL: isActive ? 'bg-teal-600 text-white' : 'bg-white text-slate-700 border-slate-200',
            LEADING: isActive ? 'bg-emerald-600 text-white' : 'bg-white text-emerald-700 border-emerald-200',
            WEAKENING: isActive ? 'bg-amber-600 text-white' : 'bg-white text-amber-700 border-amber-200',
            LAGGING: isActive ? 'bg-red-600 text-white' : 'bg-white text-red-700 border-red-200',
            IMPROVING: isActive ? 'bg-blue-600 text-white' : 'bg-white text-blue-700 border-blue-200',
          }
          return (
            <button
              key={q}
              onClick={() => setQuadrantFilter(q)}
              className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${colorMap[q]}`}
            >
              {q === 'ALL' ? 'All' : q.charAt(0) + q.slice(1).toLowerCase()} ({count})
            </button>
          )
        })}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">
            Sector Rankings
          </h2>
          {sectorsLoading ? (
            <LoadingSkeleton type="table" rows={8} />
          ) : (
            <RSRankingTable
              data={filteredSectors}
              onRowClick={handleSectorSelect}
              showSector
            />
          )}
        </div>

        <div className="lg:col-span-3">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">
            Relative Rotation Graph
          </h2>
          {rrgLoading ? (
            <LoadingSkeleton type="chart" />
          ) : (
            <RRGScatter
              data={rrgData}
              width={580}
              height={450}
              onPointClick={handleRRGPointClick}
            />
          )}
        </div>
      </div>

      <div>
        <RSLineChart
          data={rsLineData}
          title={`RS Line — ${displaySectorName} vs ${countryName} Index`}
        />
        <p className="mt-2 text-xs text-slate-400">
          Click a sector card or table row to view its RS line. Click a sector in the RRG chart to navigate to stock selection.
        </p>
      </div>
    </div>
  )
}
