import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FilterBar from '@/components/common/FilterBar'

describe('FilterBar', () => {
  const defaultProps = {
    selectedQuadrants: [] as ('LEADING' | 'WEAKENING' | 'LAGGING' | 'IMPROVING')[],
    onQuadrantsChange: vi.fn(),
    liquidityTier: null,
    onLiquidityChange: vi.fn(),
    rsMinimum: 0,
    onRsMinimumChange: vi.fn(),
  }

  it('renders all filter controls', () => {
    render(<FilterBar {...defaultProps} />)
    expect(screen.getByTestId('filter-bar')).toBeInTheDocument()
    expect(screen.getByTestId('quadrant-LEADING')).toBeInTheDocument()
    expect(screen.getByTestId('quadrant-WEAKENING')).toBeInTheDocument()
    expect(screen.getByTestId('quadrant-LAGGING')).toBeInTheDocument()
    expect(screen.getByTestId('quadrant-IMPROVING')).toBeInTheDocument()
    expect(screen.getByTestId('liquidity-select')).toBeInTheDocument()
    expect(screen.getByTestId('rs-minimum-slider')).toBeInTheDocument()
  })

  it('toggles quadrant checkbox on click', async () => {
    const user = userEvent.setup()
    const handler = vi.fn()
    render(<FilterBar {...defaultProps} onQuadrantsChange={handler} />)
    await user.click(screen.getByTestId('quadrant-LEADING'))
    expect(handler).toHaveBeenCalledWith(['LEADING'])
  })

  it('calls onLiquidityChange when select changes', async () => {
    const user = userEvent.setup()
    const handler = vi.fn()
    render(<FilterBar {...defaultProps} onLiquidityChange={handler} />)
    await user.selectOptions(screen.getByTestId('liquidity-select'), '1')
    expect(handler).toHaveBeenCalledWith(1)
  })

  it('shows RS minimum value', () => {
    render(<FilterBar {...defaultProps} rsMinimum={42} />)
    expect(screen.getByText('42')).toBeInTheDocument()
  })
})
