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
    adjusted_rs_score: 72.5,
    rs_momentum: 8.3,
    quadrant: 'LEADING',
    rs_pct_1m: 68,
    rs_pct_3m: 75,
    rs_pct_6m: 80,
    rs_pct_12m: 65,
    volume_ratio: 1.15,
    rs_trend: 'OUTPERFORMING',
    liquidity_tier: 1,
    extension_warning: false,
  },
  {
    instrument_id: 'FTM',
    name: 'FTSE 100',
    country: 'GB',
    sector: null,
    adjusted_rs_score: 35.2,
    rs_momentum: -8.4,
    quadrant: 'LAGGING',
    rs_pct_1m: 30,
    rs_pct_3m: 35,
    rs_pct_6m: 40,
    rs_pct_12m: 42,
    volume_ratio: 0.82,
    rs_trend: 'UNDERPERFORMING',
    liquidity_tier: 1,
    extension_warning: false,
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

  it('shows quadrant badges', () => {
    render(<RSRankingTable data={MOCK_DATA} showCountry />)

    expect(screen.getByText('Leading')).toBeInTheDocument()
    expect(screen.getByText('Lagging')).toBeInTheDocument()
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
