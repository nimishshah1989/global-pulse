import { useQuery } from '@tanstack/react-query'
import apiClient from '@/api/client'
import type { Regime } from '@/types/rs'

interface RegimeResponse {
  regime: Regime
  benchmark_price: number
  benchmark_ma200: number
  as_of: string
}

export function useRegime() {
  return useQuery<RegimeResponse>({
    queryKey: ['regime'],
    queryFn: async () => {
      const response = await apiClient.get<RegimeResponse>('/regime')
      return response.data
    },
    staleTime: 10 * 60 * 1000,
  })
}
