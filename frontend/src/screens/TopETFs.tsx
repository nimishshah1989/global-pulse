import { useState, useCallback, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import ActionBadge from '@/components/common/QuadrantBadge'
import LoadingSkeleton from '@/components/common/LoadingSkeleton'
import ErrorAlert from '@/components/common/ErrorAlert'
import BasketSelectorModal from '@/components/common/BasketSelectorModal'
import { useTopETFs } from '@/api/hooks/useRankings'
import { useAddPosition } from '@/api/hooks/useBaskets'
import type { RankingItem, Action } from '@/types/rs'

const ACTION_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Actions' },
  { value: 'BUY', label: 'Buy' },
  { value: 'ACCUMULATE', label: 'Accumulate' },
  { value: 'HOLD_DIVERGENCE', label: 'Hold (Divergence)' },
  { value: 'HOLD_FADING', label: 'Hold (Fading)' },
  { value: 'WATCH', label: 'Watch' },
  { value: 'REDUCE', label: 'Reduce' },
  { value: 'SELL', label: 'Sell' },
  { value: 'AVOID', label: 'Avoid' },
]

const COUNTRY_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Countries' },
  { value: 'US', label: 'United States' },
  { value: 'GB', label: 'United Kingdom' },
  { value: 'DE', label: 'Germany' },
  { value: 'FR', label: 'France' },
  { value: 'JP', label: 'Japan' },
  { value: 'HK', label: 'Hong Kong' },
  { value: 'CN', label: 'China' },
  { value: 'KR', label: 'South Korea' },
  { value: 'IN', label: 'India' },
  { value: 'TW', label: 'Taiwan' },
  { value: 'AU', label: 'Australia' },
  { value: 'BR', label: 'Brazil' },
  { value: 'CA', label: 'Canada' },
]

const SECTOR_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Sectors' },
  // GICS core sectors
  { value: 'technology', label: 'Technology' },
  { value: 'financials', label: 'Financials' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'industrials', label: 'Industrials' },
  { value: 'consumer_discretionary', label: 'Consumer Disc.' },
  { value: 'consumer_staples', label: 'Consumer Staples' },
  { value: 'energy', label: 'Energy' },
  { value: 'materials', label: 'Materials' },
  { value: 'real_estate', label: 'Real Estate' },
  { value: 'utilities', label: 'Utilities' },
  { value: 'communication_services', label: 'Communication' },
  // Commodity sectors
  { value: 'gold', label: 'Gold' },
  { value: 'silver', label: 'Silver' },
  { value: 'crude_oil', label: 'Oil & Gas' },
  { value: 'natural_gas', label: 'Natural Gas' },
  { value: 'commodities_broad', label: 'Commodities (Broad)' },
  // Other
  { value: 'fixed_income', label: 'Fixed Income' },
  { value: 'crypto', label: 'Crypto' },
]

import { getTrendArrow, getTrendColor, getVolumeColor } from '@/utils/trend'

/** Map sector slugs to human-readable display labels. */
const SECTOR_DISPLAY: Record<string, string> = {
  technology: 'Technology', financials: 'Financials', healthcare: 'Healthcare',
  industrials: 'Industrials', consumer_discretionary: 'Consumer Disc.',
  consumer_staples: 'Consumer Staples', energy: 'Energy', materials: 'Materials',
  real_estate: 'Real Estate', utilities: 'Utilities',
  communication_services: 'Communication', communication: 'Communication',
  semiconductors: 'Semiconductors', biotech: 'Biotech', pharma: 'Pharma',
  cybersecurity: 'Cybersecurity', cloud_computing: 'Cloud',
  artificial_intelligence: 'AI', robotics_ai: 'Robotics/AI',
  aerospace_defense: 'Aerospace & Defense', airlines: 'Airlines',
  homebuilders: 'Homebuilders', banks: 'Banks', regional_banks: 'Regional Banks',
  insurance: 'Insurance', medical_devices: 'Medical Devices',
  oil_gas_exploration: 'Oil & Gas E&P', oil_services: 'Oil Services',
  clean_energy: 'Clean Energy', solar: 'Solar', mlp_midstream: 'MLP/Midstream',
  // Commodities
  gold: 'Gold', gold_miners: 'Gold Miners', gold_miners_jr: 'Jr Gold Miners',
  silver: 'Silver', silver_miners: 'Silver Miners',
  crude_oil: 'Crude Oil', natural_gas: 'Natural Gas',
  commodities_broad: 'Commodities', agriculture: 'Agriculture',
  platinum: 'Platinum', palladium: 'Palladium', uranium: 'Uranium',
  lithium_battery: 'Lithium', copper_miners: 'Copper Miners',
  rare_earth: 'Rare Earth', metals_broad: 'Metals',
  // Fixed income
  fixed_income: 'Fixed Income', aggregate_bond: 'Bonds (Agg)',
  treasury_short: 'Treasury Short', treasury_mid: 'Treasury Mid',
  treasury_long: 'Treasury Long', high_yield: 'High Yield',
  investment_grade: 'Inv. Grade', municipal: 'Municipal',
  tips: 'TIPS', em_bond: 'EM Bonds', intl_bond: 'Int\'l Bonds',
  fixed_income_other: 'Fixed Income',
  // Crypto
  crypto: 'Crypto', bitcoin: 'Bitcoin', ethereum: 'Ethereum',
  // Style/Strategy
  dividends: 'Dividends', dividend_income: 'Dividend Income',
  broad_market: 'Broad Market', broad_equity: 'Broad Equity',
  small_cap: 'Small Cap', mid_cap: 'Mid Cap', large_cap: 'Large Cap',
  value: 'Value', growth: 'Growth', momentum: 'Momentum',
  quality: 'Quality', low_volatility: 'Low Vol',
  country_equity: 'Country Equity',
}

function formatSector(slug: string | null | undefined): string {
  if (!slug) return '--'
  return SECTOR_DISPLAY[slug] ?? slug.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function getRowBg(action: Action): string {
  if (action === 'BUY') return 'bg-emerald-50/40'
  if (action === 'ACCUMULATE') return 'bg-teal-50/30'
  return ''
}

export default function TopETFs(): JSX.Element {
  const [searchParams] = useSearchParams()
  const [actionFilter, setActionFilter] = useState(searchParams.get('action') ?? '')
  const [countryFilter, setCountryFilter] = useState(searchParams.get('country') ?? '')
  const [sectorFilter, setSectorFilter] = useState(searchParams.get('sector') ?? '')
  const [basketModalItem, setBasketModalItem] = useState<RankingItem | null>(null)

  // Sync filters from URL params on navigation
  useEffect(() => {
    const a = searchParams.get('action') ?? ''
    const c = searchParams.get('country') ?? ''
    const s = searchParams.get('sector') ?? ''
    if (a) setActionFilter(a)
    if (c) setCountryFilter(c)
    if (s) setSectorFilter(s)
  }, [searchParams])

  const { data: etfData, isLoading, error, refetch } = useTopETFs(
    actionFilter || undefined,
    countryFilter || undefined,
    sectorFilter || undefined,
    50,
  )
  const addPositionMutation = useAddPosition()

  const etfs: RankingItem[] = Array.isArray(etfData) ? etfData : []

  const handleAddToBasket = useCallback((item: RankingItem): void => {
    setBasketModalItem(item)
  }, [])

  function handleBasketSelect(basketId: string, weight: number): void {
    if (!basketModalItem) return
    addPositionMutation.mutate(
      { basketId, instrument_id: basketModalItem.instrument_id, weight },
      { onSuccess: () => setBasketModalItem(null) },
    )
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          Top ETFs
        </h1>
        <p className="text-sm text-slate-500">
          What ETFs should I invest in? Ranked by RS Score.
        </p>
      </div>

      {error && (
        <ErrorAlert
          message={error instanceof Error ? error.message : 'Unknown error'}
          onRetry={() => void refetch()}
        />
      )}

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-4 rounded-xl border border-slate-200 bg-white px-5 py-3">
        <FilterSelect label="Action" value={actionFilter} options={ACTION_OPTIONS} onChange={setActionFilter} />
        <FilterSelect label="Country" value={countryFilter} options={COUNTRY_OPTIONS} onChange={setCountryFilter} />
        <FilterSelect label="Sector" value={sectorFilter} options={SECTOR_OPTIONS} onChange={setSectorFilter} />
        {(actionFilter || countryFilter || sectorFilter) && (
          <button
            onClick={() => { setActionFilter(''); setCountryFilter(''); setSectorFilter('') }}
            className="rounded-lg px-3 py-1.5 text-xs font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-700"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Results count */}
      {!isLoading && (
        <p className="text-xs text-slate-500">
          Showing {etfs.length} ETF{etfs.length !== 1 ? 's' : ''}
        </p>
      )}

      {/* Main Table */}
      {isLoading ? (
        <LoadingSkeleton type="table" rows={12} />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="sticky top-0 z-10 border-b border-slate-200 bg-slate-50">
              <tr>
                <Th>ETF Name</Th>
                <Th>Country</Th>
                <Th>Sector</Th>
                <Th>Action</Th>
                <Th>RS Score</Th>
                <Th>Momentum%</Th>
                <Th>Volume</Th>
                <Th>Price Trend</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {etfs.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-4 py-8 text-center text-sm text-slate-400">
                    No ETFs match the selected filters. Try broadening your criteria.
                  </td>
                </tr>
              )}
              {etfs.map((etf) => (
                <tr key={etf.instrument_id} className={`transition-colors hover:bg-slate-50 ${getRowBg(etf.action)}`}>
                  <td className="px-4 py-3">
                    <div>
                      <span className="font-mono font-semibold text-teal-700">
                        {etf.instrument_id.replace(/_US$/, '')}
                      </span>
                      <span className="ml-2 text-slate-500">{etf.name}</span>
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-slate-600">
                    {etf.country ?? '--'}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-slate-600">
                    {formatSector(etf.sector)}
                  </td>
                  <td className="px-4 py-3">
                    <ActionBadge action={etf.action} />
                  </td>
                  <td className="px-4 py-3 font-mono font-semibold text-slate-900">
                    {etf.rs_score.toFixed(1)}
                  </td>
                  <td className="px-4 py-3">
                    <MomentumCell value={etf.rs_momentum_pct} trend={etf.momentum_trend} />
                  </td>
                  <td className="px-4 py-3">
                    <VolumeCell character={etf.volume_character} />
                  </td>
                  <td className="px-4 py-3">
                    <span className={`font-medium ${getTrendColor(etf.price_trend)}`}>
                      {getTrendArrow(etf.price_trend)} {etf.price_trend ?? '--'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleAddToBasket(etf)}
                      className="whitespace-nowrap rounded-lg bg-teal-50 px-2.5 py-1 text-xs font-semibold text-teal-700 hover:bg-teal-100"
                    >
                      + Basket
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <BasketSelectorModal
        isOpen={basketModalItem !== null}
        instrumentId={basketModalItem?.instrument_id ?? ''}
        instrumentName={basketModalItem?.name ?? ''}
        onClose={() => setBasketModalItem(null)}
        onSelect={handleBasketSelect}
        isAdding={addPositionMutation.isPending}
      />
    </div>
  )
}

/* ---------- Sub-components ---------- */

function Th({ children }: { children?: React.ReactNode }): JSX.Element {
  return (
    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
      {children}
    </th>
  )
}

function FilterSelect({ label, value, options, onChange }: {
  label: string
  value: string
  options: { value: string; label: string }[]
  onChange: (v: string) => void
}): JSX.Element {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  )
}

function MomentumCell({ value, trend }: { value: number | null; trend: string | null }): JSX.Element {
  if (value === null || value === undefined) {
    return <span className="font-mono text-slate-400">--</span>
  }
  const color = trend === 'ACCELERATING' ? 'text-emerald-600' : trend === 'DECELERATING' ? 'text-red-600' : 'text-slate-600'
  return <span className={`font-mono font-medium ${color}`}>{value > 0 ? '+' : ''}{value.toFixed(1)}%</span>
}

function VolumeCell({ character }: { character: string | null }): JSX.Element {
  return <span className={`text-xs font-medium ${getVolumeColor(character)}`}>{character ?? '--'}</span>
}
