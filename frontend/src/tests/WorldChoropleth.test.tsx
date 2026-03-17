import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import type { RankingItem } from '@/types/rs'

// Mock react-simple-maps since it relies on fetch for TopoJSON
vi.mock('react-simple-maps', () => ({
  ComposableMap: ({ children, ...props }: Record<string, unknown>) => (
    <svg data-testid="composable-map" {...props}>{children as React.ReactNode}</svg>
  ),
  Geographies: ({ children }: { children: (args: { geographies: never[] }) => React.ReactNode }) =>
    children({ geographies: [] }),
  Geography: () => <path data-testid="geography" />,
  ZoomableGroup: ({ children }: { children: React.ReactNode }) => <g>{children}</g>,
}))

import WorldChoropleth from '@/components/maps/WorldChoropleth'

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
]

describe('WorldChoropleth', () => {
  it('renders without crashing', () => {
    render(
      <MemoryRouter>
        <WorldChoropleth data={MOCK_DATA} />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('world-choropleth')).toBeInTheDocument()
  })

  it('contains an SVG element', () => {
    render(
      <MemoryRouter>
        <WorldChoropleth data={MOCK_DATA} />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('composable-map')).toBeInTheDocument()
  })

  it('renders the color legend', () => {
    render(
      <MemoryRouter>
        <WorldChoropleth data={MOCK_DATA} />
      </MemoryRouter>,
    )

    expect(screen.getByText('Weak')).toBeInTheDocument()
    expect(screen.getByText('Strong')).toBeInTheDocument()
  })
})
