import { describe, it, expect } from 'vitest'
import { formatCurrency, formatPercent, formatRS, formatVolume } from '@/utils/format'

describe('formatCurrency', () => {
  it('formats USD values correctly', () => {
    expect(formatCurrency(1234567.89)).toBe('$1,234,567.89')
  })

  it('formats with different currencies', () => {
    expect(formatCurrency(1000, 'EUR')).toContain('1,000')
  })

  it('handles zero', () => {
    expect(formatCurrency(0)).toBe('$0.00')
  })

  it('handles negative values', () => {
    expect(formatCurrency(-500.5)).toBe('-$500.50')
  })
})

describe('formatPercent', () => {
  it('adds + prefix for positive values', () => {
    expect(formatPercent(12.345)).toBe('+12.35%')
  })

  it('shows - prefix for negative values', () => {
    expect(formatPercent(-5.678)).toBe('-5.68%')
  })

  it('handles zero', () => {
    expect(formatPercent(0)).toBe('0.00%')
  })
})

describe('formatRS', () => {
  it('formats to 2 decimal places', () => {
    expect(formatRS(67.456)).toBe('67.46')
  })

  it('pads with trailing zeros', () => {
    expect(formatRS(50)).toBe('50.00')
  })
})

describe('formatVolume', () => {
  it('formats billions', () => {
    expect(formatVolume(2_500_000_000)).toBe('2.5B')
  })

  it('formats millions', () => {
    expect(formatVolume(1_200_000)).toBe('1.2M')
  })

  it('formats thousands', () => {
    expect(formatVolume(45_000)).toBe('45.0K')
  })

  it('formats small numbers as-is', () => {
    expect(formatVolume(999)).toBe('999')
  })
})
