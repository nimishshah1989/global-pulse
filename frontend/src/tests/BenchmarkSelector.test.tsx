import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect } from 'vitest'
import BenchmarkSelector from '@/components/common/BenchmarkSelector'

describe('BenchmarkSelector', () => {
  it('renders the benchmark dropdown', () => {
    render(<BenchmarkSelector />)

    const select = screen.getByLabelText('Benchmark:')
    expect(select).toBeInTheDocument()
  })

  it('renders all benchmark options', () => {
    render(<BenchmarkSelector />)

    expect(screen.getByText('MSCI ACWI')).toBeInTheDocument()
    expect(screen.getByText('Gold')).toBeInTheDocument()
    expect(screen.getByText('USD Cash')).toBeInTheDocument()
    expect(screen.getByText('Emerging Markets')).toBeInTheDocument()
    expect(screen.getByText('Developed ex-US')).toBeInTheDocument()
  })

  it('defaults to ACWI', () => {
    render(<BenchmarkSelector />)

    const select = screen.getByLabelText('Benchmark:') as HTMLSelectElement
    expect(select.value).toBe('ACWI')
  })

  it('handles selection change', async () => {
    const user = userEvent.setup()
    render(<BenchmarkSelector />)

    const select = screen.getByLabelText('Benchmark:')
    await user.selectOptions(select, 'GLD')

    expect((select as HTMLSelectElement).value).toBe('GLD')
  })
})
