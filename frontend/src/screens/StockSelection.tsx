import { useState, useMemo, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import type { Quadrant, RankingItem } from '@/types/rs'
import Breadcrumb from '@/components/layout/Breadcrumb'
import FilterBar from '@/components/common/FilterBar'
import StockRankingTable from '@/components/tables/StockRankingTable'
import RRGScatter from '@/components/charts/RRGScatter'
import BasketSelectorModal from '@/components/common/BasketSelectorModal'
import LoadingSkeleton from '@/components/common/LoadingSkeleton'
import ErrorAlert from '@/components/common/ErrorAlert'
import { useStockRankings } from '@/api/hooks/useRankings'
import { useStockRRG } from '@/api/hooks/useRRG'
import { useAddPosition } from '@/api/hooks/useBaskets'
import { MOCK_STOCK_DATA, getMockStockRRGData } from '@/data/mockStockData'

function formatSectorName(slug: string): string {
  return slug
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
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

  const stocks = stockData ?? MOCK_STOCK_DATA
  const rrgData = rrgApiData ?? getMockStockRRGData()

  const [selectedQuadrants, setSelectedQuadrants] = useState<Quadrant[]>([])
  const [liquidityTier, setLiquidityTier] = useState<number | null>(null)
  const [rsMinimum, setRsMinimum] = useState(0)
  const [basketModalItem, setBasketModalItem] = useState<RankingItem | null>(null)

  const addPositionMutation = useAddPosition()

  const filteredStocks = useMemo(() => {
    return stocks.filter((stock) => {
      if (selectedQuadrants.length > 0 && !selectedQuadrants.includes(stock.quadrant)) {
        return false
      }
      if (liquidityTier !== null && stock.liquidity_tier !== liquidityTier) {
        return false
      }
      if (stock.adjusted_rs_score < rsMinimum) {
        return false
      }
      return true
    })
  }, [stocks, selectedQuadrants, liquidityTier, rsMinimum])

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
          🔍 {formatSectorName(sectorSlug ?? '')} — {countryCode}
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

      <FilterBar
        selectedQuadrants={selectedQuadrants}
        onQuadrantsChange={setSelectedQuadrants}
        liquidityTier={liquidityTier}
        onLiquidityChange={setLiquidityTier}
        rsMinimum={rsMinimum}
        onRsMinimumChange={setRsMinimum}
      />

      {stocksLoading ? (
        <LoadingSkeleton type="table" rows={12} />
      ) : (
        <StockRankingTable
          data={filteredStocks}
          onAddToBasket={handleAddToBasket}
        />
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
