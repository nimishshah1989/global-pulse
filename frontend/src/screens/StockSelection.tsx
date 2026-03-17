import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import type { Quadrant, RankingItem } from '@/types/rs'
import Breadcrumb from '@/components/layout/Breadcrumb'
import FilterBar from '@/components/common/FilterBar'
import StockRankingTable from '@/components/tables/StockRankingTable'
import RRGScatter from '@/components/charts/RRGScatter'
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

  const [selectedQuadrants, setSelectedQuadrants] = useState<Quadrant[]>([])
  const [liquidityTier, setLiquidityTier] = useState<number | null>(null)
  const [rsMinimum, setRsMinimum] = useState(0)

  const filteredStocks = useMemo(() => {
    return MOCK_STOCK_DATA.filter((stock) => {
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
  }, [selectedQuadrants, liquidityTier, rsMinimum])

  const rrgData = useMemo(() => getMockStockRRGData(), [])

  function handleAddToBasket(item: RankingItem): void {
    // Placeholder — would open basket selector modal
    console.log('Add to basket:', item.instrument_id)
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

      <FilterBar
        selectedQuadrants={selectedQuadrants}
        onQuadrantsChange={setSelectedQuadrants}
        liquidityTier={liquidityTier}
        onLiquidityChange={setLiquidityTier}
        rsMinimum={rsMinimum}
        onRsMinimumChange={setRsMinimum}
      />

      <StockRankingTable
        data={filteredStocks}
        onAddToBasket={handleAddToBasket}
      />

      <div>
        <h2 className="mb-2 text-lg font-semibold text-slate-900">Stock RRG</h2>
        <RRGScatter data={rrgData} height={350} />
      </div>
    </div>
  )
}
