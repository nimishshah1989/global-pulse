import { render, screen } from '@testing-library/react'
import StockRankingTable from '@/components/tables/StockRankingTable'
import type { RankingItem } from '@/types/rs'

const mockStocks: RankingItem[] = [
  {
    instrument_id: 'AAPL_US',
    name: 'Apple Inc',
    country: 'US',
    sector: 'technology',
    adjusted_rs_score: 72.8,
    rs_momentum: 3.2,
    quadrant: 'LEADING',
    rs_pct_1m: 68,
    rs_pct_3m: 72,
    rs_pct_6m: 75,
    rs_pct_12m: 73,
    volume_ratio: 1.05,
    rs_trend: 'OUTPERFORMING',
    liquidity_tier: 1,
    extension_warning: false,
  },
  {
    instrument_id: 'NVDA_US',
    name: 'NVIDIA Corp',
    country: 'US',
    sector: 'technology',
    adjusted_rs_score: 92.4,
    rs_momentum: 18.3,
    quadrant: 'LEADING',
    rs_pct_1m: 96,
    rs_pct_3m: 97,
    rs_pct_6m: 95,
    rs_pct_12m: 91,
    volume_ratio: 1.45,
    rs_trend: 'OUTPERFORMING',
    liquidity_tier: 1,
    extension_warning: true,
  },
]

describe('StockRankingTable', () => {
  it('renders stock data correctly', () => {
    render(<StockRankingTable data={mockStocks} />)
    expect(screen.getByTestId('stock-ranking-table')).toBeInTheDocument()
    expect(screen.getByText('Apple Inc')).toBeInTheDocument()
    expect(screen.getByText('NVIDIA Corp')).toBeInTheDocument()
  })

  it('shows Add to Basket buttons when handler provided', () => {
    const handler = vi.fn()
    render(<StockRankingTable data={mockStocks} onAddToBasket={handler} />)
    const buttons = screen.getAllByTestId('add-to-basket-btn')
    expect(buttons.length).toBe(2)
  })

  it('shows extension warning badge for flagged stocks', () => {
    render(<StockRankingTable data={mockStocks} onAddToBasket={vi.fn()} />)
    expect(screen.getByText('Extended')).toBeInTheDocument()
  })

  it('displays RS scores in font-mono', () => {
    render(<StockRankingTable data={mockStocks} />)
    const scoreElements = screen.getAllByText('92.4')
    expect(scoreElements[0].className).toContain('font-mono')
  })
})
