import { render, screen } from '@testing-library/react'
import StockRankingTable from '@/components/tables/StockRankingTable'
import type { RankingItem } from '@/types/rs'

const mockStocks: RankingItem[] = [
  {
    instrument_id: 'AAPL_US',
    name: 'Apple Inc',
    country: 'US',
    sector: 'technology',
    asset_type: 'stock',
    rs_line: 107.8,
    rs_ma: 104.9,
    price_trend: 'OUTPERFORMING',
    rs_momentum_pct: 3.2,
    momentum_trend: 'ACCELERATING',
    volume_character: 'NEUTRAL',
    action: 'ACCUMULATE',
    rs_score: 72.8,
    regime: 'RISK_ON',
  },
  {
    instrument_id: 'NVDA_US',
    name: 'NVIDIA Corp',
    country: 'US',
    sector: 'technology',
    asset_type: 'stock',
    rs_line: 118.5,
    rs_ma: 110.2,
    price_trend: 'OUTPERFORMING',
    rs_momentum_pct: 18.3,
    momentum_trend: 'ACCELERATING',
    volume_character: 'ACCUMULATION',
    action: 'BUY',
    rs_score: 92.4,
    regime: 'RISK_ON',
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

  it('displays RS scores in font-mono', () => {
    render(<StockRankingTable data={mockStocks} />)
    const scoreElements = screen.getAllByText('92.4')
    expect(scoreElements[0].className).toContain('font-mono')
  })
})
