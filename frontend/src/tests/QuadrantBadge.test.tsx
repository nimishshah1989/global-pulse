import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import QuadrantBadge from '@/components/common/QuadrantBadge'
import type { Quadrant } from '@/types/rs'

describe('QuadrantBadge', () => {
  const cases: { quadrant: Quadrant; label: string; colorClass: string }[] = [
    { quadrant: 'LEADING', label: 'Leading', colorClass: 'bg-emerald-100' },
    { quadrant: 'WEAKENING', label: 'Weakening', colorClass: 'bg-amber-100' },
    { quadrant: 'LAGGING', label: 'Lagging', colorClass: 'bg-red-100' },
    { quadrant: 'IMPROVING', label: 'Improving', colorClass: 'bg-blue-100' },
  ]

  cases.forEach(({ quadrant, label, colorClass }) => {
    it(`renders ${quadrant} with correct text and color`, () => {
      render(<QuadrantBadge quadrant={quadrant} />)

      const badge = screen.getByText(label)
      expect(badge).toBeInTheDocument()
      expect(badge.className).toContain(colorClass)
    })
  })
})
