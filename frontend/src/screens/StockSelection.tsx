import { useState, useMemo, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import type { RankingItem, Action } from '@/types/rs'
import Breadcrumb from '@/components/layout/Breadcrumb'
import ActionBadge from '@/components/common/QuadrantBadge'
import RRGScatter from '@/components/charts/RRGScatter'
import BasketSelectorModal from '@/components/common/BasketSelectorModal'
import LoadingSkeleton from '@/components/common/LoadingSkeleton'
import ErrorAlert from '@/components/common/ErrorAlert'
import { useStockRankings } from '@/api/hooks/useRankings'
import { useStockRRG } from '@/api/hooks/useRRG'
import { useAddPosition } from '@/api/hooks/useBaskets'
import { getMockStockRRGData } from '@/data/mockStockData'

type ActionFilterGroup = 'ALL' | 'BUY' | 'HOLD' | 'SELL' | 'WATCH' | 'ACCUMULATE' | 'REDUCE' | 'AVOID'

const HOLD_ACTIONS: Action[] = ['HOLD_DIVERGENCE', 'HOLD_FADING']

const FILTER_GROUPS: ActionFilterGroup[] = ['ALL', 'BUY', 'HOLD', 'SELL', 'WATCH', 'ACCUMULATE', 'REDUCE', 'AVOID']

function formatSectorName(slug: string): string {
  return slug
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function matchesActionFilter(action: Action, filter: ActionFilterGroup): boolean {
  if (filter === 'ALL') return true
  if (filter === 'HOLD') return HOLD_ACTIONS.includes(action)
  return action === filter
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

export default function StockSelection(): JSX.Element {
  const { countryCode, sectorSlug } = useParams<{
    countryCode: string
    sectorSlug: string
  }>()

  const code = countryCode ?? ''
  const sector = sectorSlug ?? ''

  const { data: stockData, isLoading: stocksLoading, error: stocksError, refetch: refetchStocks } = useStockRankings(code, sector)
  const { data: rrgApiData, isLoading: rrgLoading } = useStockRRG(code, sector)

  const stocks: RankingItem[] = Array.isArray(stockData) ? stockData : []
  const rrgData = rrgApiData ?? (stocks.length > 0 ? getMockStockRRGData() : [])

  const [actionFilter, setActionFilter] = useState<ActionFilterGroup>('ALL')
  const [rsMinimum, setRsMinimum] = useState(0)
  const [basketModalItem, setBasketModalItem] = useState<RankingItem | null>(null)

  const addPositionMutation = useAddPosition()

  const filteredStocks = useMemo(() => {
    return stocks.filter((stock) => {
      if (!matchesActionFilter(stock.action, actionFilter)) return false
      if (stock.rs_score < rsMinimum) return false
      return true
    })
  }, [stocks, actionFilter, rsMinimum])

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
        <Breadcrumb />
        <h1 className="mt-2 text-2xl font-bold text-slate-900">
          {formatSectorName(sectorSlug ?? '')} — {countryCode}
        </h1>
        <p className="text-sm text-slate-500">
          Which stocks are leading this sector?
        </p>
      </div>

      {stocksError && (
        <ErrorAlert
          message={stocksError instanceof Error ? stocksError.message : 'Unknown error'}
          onRetry={() => void refetchStocks()}
        />
      )}

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-6 rounded-xl border border-slate-200 bg-white px-5 py-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Action</span>
          <div className="flex flex-wrap gap-1">
            {FILTER_GROUPS.map((f) => (
              <button
                key={f}
                onClick={() => setActionFilter(f)}
                className={`rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors ${
                  actionFilter === f
                    ? 'bg-teal-600 text-white border-teal-600'
                    : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                }`}
              >
                {f === 'ALL' ? 'All' : f.charAt(0) + f.slice(1).toLowerCase()}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">RS Min</span>
          <input
            type="range"
            min={0}
            max={100}
            value={rsMinimum}
            onChange={(e) => setRsMinimum(Number(e.target.value))}
            className="h-1.5 w-24 cursor-pointer appearance-none rounded-full bg-slate-200 accent-teal-600"
          />
          <span className="font-mono text-sm font-medium text-slate-700">{rsMinimum}</span>
        </div>
      </div>

      {/* Stock table */}
      {stocksLoading ? (
        <LoadingSkeleton type="table" rows={12} />
      ) : stocks.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white px-8 py-16 text-center">
          <p className="text-sm text-slate-500">No stock data available for this sector yet.</p>
          <p className="mt-1 text-xs text-slate-400">Stock RS scores are computed once constituent data is loaded.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="sticky top-0 z-10 border-b border-slate-200 bg-slate-50">
              <tr>
                <Th>Ticker</Th>
                <Th>Name</Th>
                <Th>Action</Th>
                <Th>RS Score</Th>
                <Th>Price Trend</Th>
                <Th>Momentum</Th>
                <Th>Volume</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredStocks.map((stock) => (
                <tr key={stock.instrument_id} className="transition-colors hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <span className="font-mono font-semibold text-teal-700">
                      {stock.instrument_id.replace(/_US$/, '')}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 font-medium text-slate-900">
                    {stock.name}
                  </td>
                  <td className="px-4 py-3">
                    <ActionBadge action={stock.action} />
                  </td>
                  <td className="px-4 py-3 font-mono font-semibold text-slate-900">
                    {stock.rs_score.toFixed(1)}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`font-medium ${getTrendColor(stock.price_trend)}`}>
                      {getTrendArrow(stock.price_trend)} {stock.price_trend ?? '--'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <MomentumCell value={stock.rs_momentum_pct} trend={stock.momentum_trend} />
                  </td>
                  <td className="px-4 py-3">
                    <VolumeCell character={stock.volume_character} />
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleAddToBasket(stock)}
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

      <div>
        <h2 className="mb-2 text-lg font-semibold text-slate-900">Stock RRG</h2>
        {rrgLoading ? (
          <LoadingSkeleton type="chart" />
        ) : (
          <RRGScatter data={rrgData} height={350} />
        )}
      </div>

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

function MomentumCell({ value, trend }: { value: number | null; trend: string | null }): JSX.Element {
  if (value === null || value === undefined) {
    return <span className="font-mono text-slate-400">--</span>
  }
  const color = trend === 'ACCELERATING' ? 'text-emerald-600' : trend === 'DECELERATING' ? 'text-red-600' : 'text-slate-600'
  return <span className={`font-mono font-medium ${color}`}>{value > 0 ? '+' : ''}{value.toFixed(1)}%</span>
}

function VolumeCell({ character }: { character: string | null }): JSX.Element {
  const color = character === 'ACCUMULATION' ? 'text-emerald-600'
    : character === 'DISTRIBUTION' ? 'text-red-500'
    : 'text-slate-500'
  return <span className={`text-xs font-medium ${color}`}>{character ?? '--'}</span>
}
