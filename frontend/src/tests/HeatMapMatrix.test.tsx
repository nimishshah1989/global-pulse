import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import HeatMapMatrix from '@/components/tables/HeatMapMatrix'
import type { HeatMapCellData } from '@/components/tables/HeatMapMatrix'

const countries = ['US', 'JP', 'IN']
const sectors = ['Technology', 'Financials']

const matrix: Record<string, Record<string, HeatMapCellData>> = {
  US: {
    Technology: { score: 78, quadrant: 'BUY' },
    Financials: { score: 65, quadrant: 'ACCUMULATE' },
  },
  JP: {
    Technology: { score: 45, quadrant: 'REDUCE' },
    Financials: { score: 58, quadrant: 'HOLD_FADING' },
  },
  IN: {
    Technology: { score: 62, quadrant: 'ACCUMULATE' },
    Financials: { score: 35, quadrant: 'WATCH' },
  },
}

describe('HeatMapMatrix', () => {
  it('renders grid with correct dimensions', () => {
    render(
      <HeatMapMatrix
        countries={countries}
        sectors={sectors}
        matrix={matrix}
        mode="score"
        onCellClick={vi.fn()}
      />,
    )
    expect(screen.getByTestId('heatmap-matrix')).toBeInTheDocument()
    // 3 countries x 2 sectors = 6 cells
    expect(screen.getByTestId('cell-US-Technology')).toBeInTheDocument()
    expect(screen.getByTestId('cell-JP-Financials')).toBeInTheDocument()
    expect(screen.getByTestId('cell-IN-Technology')).toBeInTheDocument()
  })

  it('shows scores in score mode', () => {
    render(
      <HeatMapMatrix
        countries={countries}
        sectors={sectors}
        matrix={matrix}
        mode="score"
        onCellClick={vi.fn()}
      />,
    )
    expect(screen.getByTestId('cell-US-Technology').textContent).toBe('78')
  })

  it('shows action labels in quadrant mode', () => {
    render(
      <HeatMapMatrix
        countries={countries}
        sectors={sectors}
        matrix={matrix}
        mode="quadrant"
        onCellClick={vi.fn()}
      />,
    )
    // 'B' for BUY in US-Technology
    expect(screen.getByTestId('cell-US-Technology').textContent).toBe('B')
  })

  it('calls onCellClick when cell is clicked', async () => {
    const user = userEvent.setup()
    const handler = vi.fn()
    render(
      <HeatMapMatrix
        countries={countries}
        sectors={sectors}
        matrix={matrix}
        mode="score"
        onCellClick={handler}
      />,
    )
    await user.click(screen.getByTestId('cell-JP-Technology'))
    expect(handler).toHaveBeenCalledWith('JP', 'Technology')
  })
})
