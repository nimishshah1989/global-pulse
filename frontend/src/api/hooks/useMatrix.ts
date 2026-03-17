import { useQuery } from '@tanstack/react-query'
import apiClient from '@/api/client'

export interface MatrixCell {
  country: string
  sector: string
  adjusted_rs_score: number
  quadrant: string
}

export interface MatrixData {
  countries: string[]
  sectors: string[]
  cells: MatrixCell[]
  country_scores: Record<string, number>
  sector_scores: Record<string, number>
}

export function useMatrix() {
  return useQuery<MatrixData>({
    queryKey: ['matrix'],
    queryFn: async () => {
      const response = await apiClient.get<MatrixData>('/matrix')
      return response.data
    },
  })
}
