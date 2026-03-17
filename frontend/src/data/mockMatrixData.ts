import type { Quadrant } from '@/types/rs'

export const MATRIX_COUNTRIES = [
  'US', 'GB', 'DE', 'FR', 'JP', 'HK', 'CN', 'KR', 'IN', 'TW', 'AU', 'BR', 'CA',
] as const

export const MATRIX_SECTORS = [
  'Technology', 'Financials', 'Healthcare', 'Industrials', 'Consumer Disc.',
  'Consumer Staples', 'Energy', 'Materials', 'Real Estate', 'Utilities',
  'Communication',
] as const

export const COUNTRY_LABELS: Record<string, string> = {
  US: '\u{1F1FA}\u{1F1F8} US',
  GB: '\u{1F1EC}\u{1F1E7} UK',
  DE: '\u{1F1E9}\u{1F1EA} DE',
  FR: '\u{1F1EB}\u{1F1F7} FR',
  JP: '\u{1F1EF}\u{1F1F5} JP',
  HK: '\u{1F1ED}\u{1F1F0} HK',
  CN: '\u{1F1E8}\u{1F1F3} CN',
  KR: '\u{1F1F0}\u{1F1F7} KR',
  IN: '\u{1F1EE}\u{1F1F3} IN',
  TW: '\u{1F1F9}\u{1F1FC} TW',
  AU: '\u{1F1E6}\u{1F1FA} AU',
  BR: '\u{1F1E7}\u{1F1F7} BR',
  CA: '\u{1F1E8}\u{1F1E6} CA',
}

function getQuadrant(score: number, momentum: number): Quadrant {
  if (score > 50 && momentum > 0) return 'LEADING'
  if (score > 50 && momentum <= 0) return 'WEAKENING'
  if (score <= 50 && momentum > 0) return 'IMPROVING'
  return 'LAGGING'
}

// Seed-based deterministic pseudo-random for consistent mock data
function seededScore(country: string, sector: string): number {
  let hash = 0
  const str = country + sector
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0
  }
  return Math.abs(hash % 85) + 8
}

export interface MatrixCellData {
  score: number
  quadrant: Quadrant
}

export function generateMockMatrix(): Record<string, Record<string, MatrixCellData>> {
  const matrix: Record<string, Record<string, MatrixCellData>> = {}

  for (const country of MATRIX_COUNTRIES) {
    matrix[country] = {}
    for (const sector of MATRIX_SECTORS) {
      const score = seededScore(country, sector)
      const momentum = score > 50 ? (Math.random() > 0.3 ? 5 : -3) : (Math.random() > 0.6 ? 4 : -6)
      matrix[country][sector] = {
        score,
        quadrant: getQuadrant(score, momentum),
      }
    }
  }
  return matrix
}

export const MOCK_COUNTRY_SCORES: Record<string, number> = {
  US: 72.5, GB: 35.2, DE: 61.3, FR: 52.7, JP: 68.1, HK: 38.5,
  CN: 28.9, KR: 55.2, IN: 65.8, TW: 58.4, AU: 45.1, BR: 42.3, CA: 48.6,
}

export const MOCK_SECTOR_SCORES: Record<string, number> = {
  'Technology': 74.2, 'Financials': 62.8, 'Healthcare': 58.5, 'Industrials': 55.1,
  'Consumer Disc.': 48.7, 'Consumer Staples': 42.3, 'Energy': 45.8, 'Materials': 40.2,
  'Real Estate': 32.6, 'Utilities': 28.4, 'Communication': 51.9,
}
