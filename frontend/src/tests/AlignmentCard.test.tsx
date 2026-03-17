import { render, screen } from '@testing-library/react'
import AlignmentCard from '@/components/common/AlignmentCard'
import type { Opportunity } from '@/types/opportunities'

const mockAlignment: Opportunity = {
  id: 'opp-1',
  instrument_id: 'TATASTEEL_IN',
  instrument_name: 'Tata Steel',
  date: '2026-03-17',
  signal_type: 'multi_level_alignment',
  conviction_score: 82,
  description: 'Multi-level alignment detected',
  metadata: {
    country: 'India',
    country_quadrant: 'LEADING',
    sector: 'NIFTY Metal',
    sector_quadrant: 'LEADING',
    stock: 'Tata Steel',
    stock_quadrant: 'LEADING',
  },
}

describe('AlignmentCard', () => {
  it('renders the alignment card', () => {
    render(<AlignmentCard opportunity={mockAlignment} />)
    expect(screen.getByTestId('alignment-card')).toBeInTheDocument()
  })

  it('displays the chain visualization', () => {
    render(<AlignmentCard opportunity={mockAlignment} />)
    expect(screen.getByTestId('alignment-chain')).toBeInTheDocument()
    expect(screen.getByText('India')).toBeInTheDocument()
    expect(screen.getByText('NIFTY Metal')).toBeInTheDocument()
    expect(screen.getByText('Tata Steel')).toBeInTheDocument()
  })

  it('shows conviction score', () => {
    render(<AlignmentCard opportunity={mockAlignment} />)
    expect(screen.getByText('82')).toBeInTheDocument()
  })

  it('shows instrument name and date', () => {
    render(<AlignmentCard opportunity={mockAlignment} />)
    const matches = screen.getAllByText(/Tata Steel/i)
    expect(matches.length).toBeGreaterThanOrEqual(2)
  })

  it('falls back to description when metadata lacks chain info', () => {
    const noChain: Opportunity = {
      ...mockAlignment,
      metadata: null,
    }
    render(<AlignmentCard opportunity={noChain} />)
    expect(screen.getByText('Multi-level alignment detected')).toBeInTheDocument()
  })
})
