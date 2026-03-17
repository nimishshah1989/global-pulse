import { render, screen } from '@testing-library/react'
import PerformanceStats from '@/components/common/PerformanceStats'
import type { BasketPerformance } from '@/types/baskets'

const mockPerformance: BasketPerformance = {
  cumulative_return: 11.47,
  cagr: null,
  max_drawdown: -6.82,
  sharpe_ratio: 1.24,
  pct_weeks_outperforming: 58.3,
}

describe('PerformanceStats', () => {
  it('renders all metric cards', () => {
    render(<PerformanceStats performance={mockPerformance} />)
    expect(screen.getByTestId('performance-stats')).toBeInTheDocument()
    const statCards = screen.getAllByTestId('stat-card')
    expect(statCards.length).toBe(5)
  })

  it('displays cumulative return with correct formatting', () => {
    render(<PerformanceStats performance={mockPerformance} />)
    expect(screen.getByText('+11.47%')).toBeInTheDocument()
  })

  it('displays max drawdown', () => {
    render(<PerformanceStats performance={mockPerformance} />)
    expect(screen.getByText('-6.82%')).toBeInTheDocument()
  })

  it('displays sharpe ratio', () => {
    render(<PerformanceStats performance={mockPerformance} />)
    expect(screen.getByText('1.24')).toBeInTheDocument()
  })

  it('shows N/A for null CAGR', () => {
    render(<PerformanceStats performance={mockPerformance} />)
    expect(screen.getByText('N/A')).toBeInTheDocument()
  })

  it('displays pct weeks outperforming', () => {
    render(<PerformanceStats performance={mockPerformance} />)
    expect(screen.getByText('58.3%')).toBeInTheDocument()
  })
})
