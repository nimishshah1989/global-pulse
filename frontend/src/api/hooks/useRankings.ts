import { useQuery } from '@tanstack/react-query'
import apiClient from '@/api/client'
import type { RankingItem } from '@/types/rs'

export function useCountryRankings() {
  return useQuery<RankingItem[]>({
    queryKey: ['rankings', 'countries'],
    queryFn: async () => {
      const response = await apiClient.get<RankingItem[]>('/rankings/countries')
      return response.data
    },
  })
}

export function useSectorRankings(countryCode: string) {
  return useQuery<RankingItem[]>({
    queryKey: ['rankings', 'sectors', countryCode],
    queryFn: async () => {
      const response = await apiClient.get<RankingItem[]>(`/rankings/sectors/${countryCode}`)
      return response.data
    },
    enabled: !!countryCode,
  })
}

export function useStockRankings(countryCode: string, sector: string) {
  return useQuery<RankingItem[]>({
    queryKey: ['rankings', 'stocks', countryCode, sector],
    queryFn: async () => {
      const response = await apiClient.get<RankingItem[]>(
        `/rankings/stocks/${countryCode}/${sector}`,
      )
      return response.data
    },
    enabled: !!countryCode && !!sector,
  })
}

export function useGlobalSectorRankings() {
  return useQuery<RankingItem[]>({
    queryKey: ['rankings', 'global-sectors'],
    queryFn: async () => {
      const response = await apiClient.get<RankingItem[]>('/rankings/global-sectors')
      return response.data
    },
  })
}
