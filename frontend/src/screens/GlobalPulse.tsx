import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import WorldChoropleth from '@/components/maps/WorldChoropleth'
import RegimeBanner from '@/components/common/RegimeBanner'
import BenchmarkSelector from '@/components/common/BenchmarkSelector'
import DateNavigator from '@/components/common/DateNavigator'
import LoadingSkeleton from '@/components/common/LoadingSkeleton'
import ErrorAlert from '@/components/common/ErrorAlert'
import ActionBadge from '@/components/common/QuadrantBadge'
import { useCountryRankings, useSectorRankings } from '@/api/hooks/useRankings'
import { useRegime } from '@/api/hooks/useRegime'
import { useMatrix } from '@/api/hooks/useMatrix'
import { useBenchmarkStore } from '@/store/benchmarkStore'
import type { MatrixData } from '@/api/hooks/useMatrix'
import { COUNTRY_FLAGS, COUNTRY_NAMES } from '@/data/mockCountryData'
import { getTrendLabel, getTrendLabelShort, getTrendColor, getVolumeColor } from '@/utils/trend'
import type { RankingItem, Action } from '@/types/rs'

/* ---------- Return display helpers ---------- */

function ReturnCell({ value, label }: { value: number | null | undefined; label: string }): JSX.Element {
  if (value == null) return <span className="text-slate-300">--</span>
  const color = value > 0 ? 'text-emerald-600' : value < 0 ? 'text-red-600' : 'text-slate-500'
  return (
    <div className="text-center">
      <div className={`font-mono text-xs font-semibold ${color}`}>
        {value > 0 ? '+' : ''}{value.toFixed(1)}%
      </div>
      <div className="text-[10px] text-slate-400">{label}</div>
    </div>
  )
}

function ExcessReturnBar({ value }: { value: number | null | undefined }): JSX.Element {
  if (value == null) return <span className="text-slate-300 text-[10px]">--</span>
  const color = value > 0 ? 'text-emerald-600' : value < 0 ? 'text-red-600' : 'text-slate-500'
  const bgColor = value > 0 ? 'bg-emerald-100' : value < 0 ? 'bg-red-100' : 'bg-slate-100'
  return (
    <span className={`inline-block rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold ${color} ${bgColor}`}>
      {value > 0 ? '+' : ''}{value.toFixed(1)}%
    </span>
  )
}

/* ---------- Action color helpers ---------- */

function actionBorderColor(action: Action): string {
  const map: Record<string, string> = {
    BUY: 'border-emerald-300', ACCUMULATE: 'border-teal-300',
    HOLD_DIVERGENCE: 'border-yellow-300', HOLD_FADING: 'border-yellow-300',
    WATCH: 'border-blue-300', REDUCE: 'border-orange-300',
    SELL: 'border-red-300', AVOID: 'border-slate-300',
  }
  return map[action] ?? 'border-slate-200'
}

function actionBgColor(action: Action): string {
  const map: Record<string, string> = {
    BUY: 'bg-emerald-50/60', ACCUMULATE: 'bg-teal-50/60',
    HOLD_DIVERGENCE: 'bg-yellow-50/40', HOLD_FADING: 'bg-yellow-50/40',
    WATCH: 'bg-blue-50/40', REDUCE: 'bg-orange-50/40',
    SELL: 'bg-red-50/40', AVOID: 'bg-slate-50/60',
  }
  return map[action] ?? ''
}

function matrixActionStyle(action: string): string {
  const map: Record<string, string> = {
    BUY: 'bg-emerald-100 text-emerald-800',
    ACCUMULATE: 'bg-teal-100 text-teal-800',
    HOLD_DIVERGENCE: 'bg-yellow-100 text-yellow-800',
    HOLD_FADING: 'bg-yellow-100 text-yellow-800',
    WATCH: 'bg-blue-100 text-blue-800',
    REDUCE: 'bg-orange-100 text-orange-800',
    SELL: 'bg-red-100 text-red-800',
    AVOID: 'bg-slate-100 text-slate-700',
    LEADING: 'bg-emerald-100 text-emerald-800',
    IMPROVING: 'bg-teal-100 text-teal-800',
    WEAKENING: 'bg-orange-100 text-orange-800',
    LAGGING: 'bg-red-100 text-red-800',
  }
  return map[action] ?? 'bg-slate-50 text-slate-600'
}

function actionShortLabel(action: string): string {
  const map: Record<string, string> = {
    BUY: 'Buy', ACCUMULATE: 'Acc', HOLD_DIVERGENCE: 'Hold',
    HOLD_FADING: 'Hold', WATCH: 'Watch', REDUCE: 'Red',
    SELL: 'Sell', AVOID: 'Avoid',
    LEADING: 'Buy', IMPROVING: 'Acc', WEAKENING: 'Red', LAGGING: 'Sell',
  }
  return map[action] ?? '?'
}

/* ---------- Sector Row within an expanded country ---------- */

function SectorRow({ sector, isExpanded, onToggle }: {
  sector: RankingItem
  isExpanded: boolean
  onToggle: () => void
}): JSX.Element {
  return (
    <div className={`rounded-lg border transition-all ${actionBorderColor(sector.action)} ${isExpanded ? actionBgColor(sector.action) : 'hover:bg-slate-50'}`}>
      <button onClick={onToggle} className="flex w-full items-center justify-between px-4 py-2.5 text-left">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-slate-800">{sector.name}</span>
          <ActionBadge action={sector.action} />
        </div>
        <svg className={`h-4 w-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isExpanded && (
        <div className="border-t border-slate-200/60 px-4 py-3">
          {/* Ratio returns row */}
          <div className="mb-2 flex items-center gap-3">
            <ReturnCell value={sector.return_1m} label="1M" />
            <ReturnCell value={sector.return_3m} label="3M" />
            <ReturnCell value={sector.return_6m} label="6M" />
            <ReturnCell value={sector.return_12m} label="12M" />
          </div>
          {/* Excess returns */}
          {(sector.excess_3m != null || sector.excess_6m != null) && (
            <div className="mb-2 flex items-center gap-1.5">
              <span className="text-[10px] text-slate-400">vs bench:</span>
              <ExcessReturnBar value={sector.excess_1m} />
              <ExcessReturnBar value={sector.excess_3m} />
              <ExcessReturnBar value={sector.excess_6m} />
              <ExcessReturnBar value={sector.excess_12m} />
            </div>
          )}
          <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-500">Price Trend</span>
              <span className={`font-medium ${getTrendColor(sector.price_trend)}`}>
                {getTrendLabelShort(sector.price_trend)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Volume</span>
              <span className={`font-medium ${getVolumeColor(sector.volume_character)}`}>
                {sector.volume_character ?? '--'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/* ---------- Expanded country panel with its sectors ---------- */

function CountrySectors({ countryCode }: { countryCode: string }): JSX.Element {
  const benchmark = useBenchmarkStore((state) => state.benchmark)
  const { data: sectorData, isLoading } = useSectorRankings(countryCode, null, benchmark)
  const sectors: RankingItem[] = Array.isArray(sectorData) ? sectorData : []
  const [expandedSector, setExpandedSector] = useState<string | null>(null)

  if (isLoading) return <LoadingSkeleton type="table" rows={4} />

  if (sectors.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-slate-400">
        No sector data available for this country.
      </p>
    )
  }

  return (
    <div className="space-y-1.5 pt-1">
      {sectors.map((s) => (
        <SectorRow
          key={s.instrument_id}
          sector={s}
          isExpanded={expandedSector === s.instrument_id}
          onToggle={() => setExpandedSector(expandedSector === s.instrument_id ? null : s.instrument_id)}
        />
      ))}
    </div>
  )
}

/* ---------- Country card ---------- */

function CountryCard({ item, isExpanded, onToggle, onDeepDive }: {
  item: RankingItem
  isExpanded: boolean
  onToggle: () => void
  onDeepDive: (code: string) => void
}): JSX.Element {
  const code = item.country ?? ''
  const flag = COUNTRY_FLAGS[code] ?? ''
  const name = COUNTRY_NAMES[code] ?? code

  return (
    <div className={`rounded-xl border transition-all ${isExpanded ? `${actionBorderColor(item.action)} shadow-sm` : 'border-slate-200 hover:border-slate-300 hover:shadow-sm'}`}>
      <button onClick={onToggle} className={`flex w-full items-center justify-between px-5 py-3.5 text-left ${isExpanded ? actionBgColor(item.action) : ''} rounded-t-xl`}>
        <div className="flex items-center gap-3">
          <span className="text-lg">{flag}</span>
          <span className="text-sm font-semibold text-slate-900">{name}</span>
          <ActionBadge action={item.action} />
        </div>
        <div className="flex items-center gap-3">
          {isExpanded && (
            <span className="font-mono text-xs text-slate-500">RS {item.rs_score.toFixed(1)}</span>
          )}
          <svg className={`h-4 w-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {isExpanded && (
        <div className="border-t border-slate-200/60 px-5 py-4">
          {/* Ratio returns — the primary display */}
          <div className="mb-3 rounded-lg bg-white/70 px-4 py-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">Returns</span>
              <span className={`text-xs font-medium ${getTrendColor(item.price_trend)}`}>
                {getTrendLabel(item.price_trend)}
              </span>
            </div>
            <div className="flex items-center gap-4">
              <ReturnCell value={item.return_1m} label="1M" />
              <ReturnCell value={item.return_3m} label="3M" />
              <ReturnCell value={item.return_6m} label="6M" />
              <ReturnCell value={item.return_12m} label="12M" />
              <div className="mx-2 h-8 w-px bg-slate-200" />
              <div className="text-center">
                <div className={`font-mono text-xs font-semibold ${getVolumeColor(item.volume_character)}`}>
                  {item.volume_character ?? '--'}
                </div>
                <div className="text-[10px] text-slate-400">Volume</div>
              </div>
            </div>
            {/* Excess returns vs benchmark */}
            {(item.excess_3m != null || item.excess_6m != null) && (
              <div className="mt-2 flex items-center gap-1.5 border-t border-slate-100 pt-2">
                <span className="text-[10px] text-slate-400">vs benchmark:</span>
                <ExcessReturnBar value={item.excess_1m} />
                <ExcessReturnBar value={item.excess_3m} />
                <ExcessReturnBar value={item.excess_6m} />
                <ExcessReturnBar value={item.excess_12m} />
              </div>
            )}
          </div>

          {/* Navigation links */}
          <div className="mb-3 flex justify-end gap-2">
            <button
              onClick={() => onDeepDive(code)}
              className="rounded-lg bg-primary-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-primary-700 transition-colors"
            >
              Sector Deep Dive &rarr;
            </button>
          </div>

          {/* Sectors within this country */}
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Sectors</h3>
          <CountrySectors countryCode={code} />
        </div>
      )}
    </div>
  )
}

/* ---------- Sector x Country matrix (action view) ---------- */

function SectorCountryMatrix({ matrixData }: { matrixData: MatrixData }): JSX.Element {
  const [hoveredCountry, setHoveredCountry] = useState<string | null>(null)

  if (matrixData.countries.length === 0 || matrixData.sectors.length === 0) {
    return <p className="py-4 text-center text-sm text-slate-400">No matrix data available.</p>
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50">
            <th className="sticky left-0 z-20 bg-slate-50 px-3 py-2 text-left font-semibold text-slate-500">Sector</th>
            {matrixData.countries.map((c) => (
              <th
                key={c}
                className={`px-2 py-2 text-center font-semibold text-slate-700 ${hoveredCountry === c ? 'bg-teal-50' : ''}`}
              >
                <div>{COUNTRY_FLAGS[c] ?? ''} {c}</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {matrixData.sectors.map((sector) => (
            <tr key={sector} className="group">
              <td className="sticky left-0 z-10 bg-white px-3 py-2 font-medium text-slate-900 group-hover:bg-slate-50">
                {sector}
              </td>
              {matrixData.countries.map((country) => {
                const cell = matrixData.cells.find((c) => c.country === country && c.sector === sector)
                if (!cell) {
                  return (
                    <td
                      key={country}
                      className={`px-2 py-2 text-center text-slate-300 ${hoveredCountry === country ? 'bg-teal-50' : ''}`}
                      onMouseEnter={() => setHoveredCountry(country)}
                      onMouseLeave={() => setHoveredCountry(null)}
                    >
                      -
                    </td>
                  )
                }
                return (
                  <td
                    key={country}
                    className={`px-1 py-1 text-center ${hoveredCountry === country ? 'bg-teal-50' : ''}`}
                    onMouseEnter={() => setHoveredCountry(country)}
                    onMouseLeave={() => setHoveredCountry(null)}
                  >
                    <span className={`inline-block min-w-[2.5rem] rounded px-1.5 py-1 font-semibold ${matrixActionStyle(cell.action)}`}>
                      {actionShortLabel(cell.action)}
                    </span>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ========== MAIN PAGE ========== */

export default function GlobalPulse(): JSX.Element {
  const navigate = useNavigate()
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const benchmark = useBenchmarkStore((state) => state.benchmark)
  const { data: countryData, isLoading: countriesLoading, error: countriesError, refetch: refetchCountries } = useCountryRankings(selectedDate, benchmark)
  const { data: regimeData } = useRegime()
  const { data: matrixData, isLoading: matrixLoading } = useMatrix()
  const [expandedCountry, setExpandedCountry] = useState<string | null>(null)

  const rankings: RankingItem[] = Array.isArray(countryData) ? countryData : []
  const sorted = [...rankings].sort((a, b) => b.rs_score - a.rs_score)

  const toggleCountry = useCallback((code: string) => {
    setExpandedCountry((prev) => (prev === code ? null : code))
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-slate-900">Global Pulse</h1>
        <div className="flex items-center gap-4">
          <BenchmarkSelector />
          <DateNavigator selectedDate={selectedDate} onDateChange={setSelectedDate} />
        </div>
      </div>

      {regimeData && <RegimeBanner regime={regimeData.regime} />}

      {countriesError && (
        <ErrorAlert
          message={countriesError instanceof Error ? countriesError.message : 'Unknown error'}
          onRetry={() => void refetchCountries()}
        />
      )}

      {/* World Map */}
      {countriesLoading ? (
        <LoadingSkeleton type="chart" />
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <WorldChoropleth data={rankings} onCountryClick={(code) => {
            setExpandedCountry((prev) => (prev === code ? null : code))
            // Scroll to country cards section
            document.getElementById('country-rankings')?.scrollIntoView({ behavior: 'smooth' })
          }} />
        </div>
      )}

      {/* Country Cards — expandable drill-down */}
      <div id="country-rankings">
        <h2 className="mb-3 text-lg font-semibold text-slate-800">Country Rankings</h2>
        {countriesLoading ? (
          <LoadingSkeleton type="table" rows={8} />
        ) : sorted.length === 0 ? (
          <p className="py-4 text-center text-sm text-slate-400">No country data available.</p>
        ) : (
          <div className="space-y-2">
            {sorted.map((item) => (
              <CountryCard
                key={item.instrument_id}
                item={item}
                isExpanded={expandedCountry === item.country}
                onToggle={() => item.country && toggleCountry(item.country)}
                onDeepDive={(code) => navigate(`/compass/country/${code}`)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Sector x Country Matrix — action view */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-slate-800">Sector x Country Matrix</h2>
        {matrixLoading ? (
          <LoadingSkeleton type="table" rows={11} />
        ) : matrixData ? (
          <SectorCountryMatrix matrixData={matrixData} />
        ) : (
          <p className="py-4 text-center text-sm text-slate-400">No matrix data available.</p>
        )}
      </div>
    </div>
  )
}
