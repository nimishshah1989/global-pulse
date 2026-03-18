import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import RSRankingTable from '@/components/tables/RSRankingTable'
import type { RankingItem } from '@/types/rs'

const MOCK_DATA: RankingItem[] = [
  {
    instrument_id: 'SPX',
    name: 'S&P 500',
    country: 'US',
    sector: null,
    asset_type: 'country_index',
    rs_line: 108.5,
    rs_ma: 104.2,
    price_trend: 'OUTPERFORMING',
    rs_momentum_pct: 8.3,
    momentum_trend: 'ACCELERATING',
    volume_character: 'ACCUMULATION',
    action: 'BUY',
    rs_score: 72.5,
    regime: 'RISK_ON',
  },
  {
    instrument_id: 'FTM',
    name: 'FTSE 100',
    country: 'GB',
    sector: null,
    asset_type: 'country_index',
    rs_line: 94.2,
    rs_ma: 98.5,
    price_trend: 'UNDERPERFORMING',
    rs_momentum_pct: -8.4,
    momentum_trend: 'DECELERATING',
    volume_character: 'DISTRIBUTION',
    action: 'SELL',
    rs_score: 35.2,
    regime: 'RISK_ON',
  },
]

describe('RSRankingTable', () => {
  it('renders data rows', () => {
    render(<RSRankingTable data={MOCK_DATA} showCountry />)

    expect(screen.getByText('United States')).toBeInTheDocument()
    expect(screen.getByText('United Kingdom')).toBeInTheDocument()
  })

  it('renders RS scores in the table', () => {
    render(<RSRankingTable data={MOCK_DATA} showCountry />)

    expect(screen.getByText('72.5')).toBeInTheDocument()
    expect(screen.getByText('35.2')).toBeInTheDocument()
  })

  it('shows action badges', () => {
    render(<RSRankingTable data={MOCK_DATA} showCountry />)

    expect(screen.getByText(/Buy/)).toBeInTheDocument()
    expect(screen.getByText(/Sell/)).toBeInTheDocument()
  })

  it('sorts by RS Score descending by default', () => {
    render(<RSRankingTable data={MOCK_DATA} showCountry />)

    const rows = screen.getAllByRole('row')
    // Row 0 is header, row 1 should be highest score (US 72.5)
    expect(rows[1]).toHaveTextContent('United States')
    expect(rows[2]).toHaveTextContent('United Kingdom')
  })

  it('calls onRowClick when a row is clicked', async () => {
    const user = userEvent.setup()
    const handleClick = vi.fn()
    render(<RSRankingTable data={MOCK_DATA} showCountry onRowClick={handleClick} />)

    await user.click(screen.getByText('United States'))
    expect(handleClick).toHaveBeenCalledWith(
      expect.objectContaining({ instrument_id: 'SPX' }),
    )
  })

  it('renders loading state', () => {
    render(<RSRankingTable data={[]} loading />)

    expect(screen.getByText('Loading rankings...')).toBeInTheDocument()
  })
})
