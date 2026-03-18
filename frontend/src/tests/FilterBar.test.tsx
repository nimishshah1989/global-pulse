import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FilterBar from '@/components/common/FilterBar'
import type { Action } from '@/types/rs'

describe('FilterBar', () => {
  const defaultProps = {
    selectedActions: [] as Action[],
    onActionsChange: vi.fn(),
    rsMinimum: 0,
    onRsMinimumChange: vi.fn(),
  }

  it('renders all filter controls', () => {
    render(<FilterBar {...defaultProps} />)
    expect(screen.getByTestId('filter-bar')).toBeInTheDocument()
    expect(screen.getByTestId('action-BUY')).toBeInTheDocument()
    expect(screen.getByTestId('action-SELL')).toBeInTheDocument()
    expect(screen.getByTestId('action-WATCH')).toBeInTheDocument()
    expect(screen.getByTestId('action-AVOID')).toBeInTheDocument()
    expect(screen.getByTestId('rs-minimum-slider')).toBeInTheDocument()
  })

  it('toggles action checkbox on click', async () => {
    const user = userEvent.setup()
    const handler = vi.fn()
    render(<FilterBar {...defaultProps} onActionsChange={handler} />)
    await user.click(screen.getByTestId('action-BUY'))
    expect(handler).toHaveBeenCalledWith(['BUY'])
  })

  it('shows RS minimum value', () => {
    render(<FilterBar {...defaultProps} rsMinimum={42} />)
    expect(screen.getByText('42')).toBeInTheDocument()
  })
})
