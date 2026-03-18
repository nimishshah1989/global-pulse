import { useQuery } from '@tanstack/react-query'
import apiClient from '@/api/client'

export interface MatrixCell {
  country: string
  sector: string
  rs_score: number
  action: string
}

/**
 * Backend returns a nested dict format:
 *   { countries, sectors, matrix: { country: { sector: { score, quadrant } } } }
 * We normalize it into a flat cells array for the frontend.
 */
interface ApiMatrixResponse {
  countries: string[]
  sectors: string[]
  matrix: Record<string, Record<string, { score: number; quadrant: string }>>
}

export interface MatrixData {
  countries: string[]
  sectors: string[]
  cells: MatrixCell[]
  country_scores: Record<string, number>
  sector_scores: Record<string, number>
}

function normalizeApiResponse(raw: ApiMatrixResponse): MatrixData {
  const cells: MatrixCell[] = []
  const countryScores: Record<string, number> = {}
  const sectorTotals: Record<string, { sum: number; count: number }> = {}

  for (const country of raw.countries) {
    const sectorMap = raw.matrix[country] ?? {}
    let countrySum = 0
    let countryCount = 0

    for (const sector of raw.sectors) {
      const cell = sectorMap[sector]
      if (cell) {
        cells.push({
          country,
          sector,
          rs_score: cell.score,
          action: cell.quadrant,
        })
        countrySum += cell.score
        countryCount++

        if (!sectorTotals[sector]) sectorTotals[sector] = { sum: 0, count: 0 }
        sectorTotals[sector].sum += cell.score
        sectorTotals[sector].count++
      }
    }

    countryScores[country] = countryCount > 0
      ? Math.round((countrySum / countryCount) * 10) / 10
      : 0
  }

  const sectorScores: Record<string, number> = {}
  for (const [sector, { sum, count }] of Object.entries(sectorTotals)) {
    sectorScores[sector] = count > 0 ? Math.round((sum / count) * 10) / 10 : 0
  }

  return { countries: raw.countries, sectors: raw.sectors, cells, country_scores: countryScores, sector_scores: sectorScores }
}

export function useMatrix() {
  return useQuery<MatrixData>({
    queryKey: ['matrix'],
    queryFn: async () => {
      const response = await apiClient.get<ApiMatrixResponse>('/matrix')
      return normalizeApiResponse(response.data)
    },
    retry: 1,
  })
}
