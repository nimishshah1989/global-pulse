import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { QuadrantBadge } from '@/components/common/QuadrantBadge'
import type { Action } from '@/types/rs'

describe('QuadrantBadge (ActionBadge)', () => {
  const cases: { action: Action; label: string; colorClass: string }[] = [
    { action: 'BUY', label: '\u25B2 Buy', colorClass: 'bg-emerald-100' },
    { action: 'SELL', label: '\u25BC Sell', colorClass: 'bg-red-100' },
    { action: 'WATCH', label: '\u25C9 Watch', colorClass: 'bg-blue-100' },
    { action: 'ACCUMULATE', label: '\u25B2 Accumulate', colorClass: 'bg-teal-100' },
  ]

  cases.forEach(({ action, label, colorClass }) => {
    it(`renders ${action} with correct text and color`, () => {
      render(<QuadrantBadge action={action} />)

      const badge = screen.getByText(label)
      expect(badge).toBeInTheDocument()
      expect(badge.className).toContain(colorClass)
    })
  })
})
