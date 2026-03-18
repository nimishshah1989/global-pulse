import { useQuery } from '@tanstack/react-query'
import apiClient from '@/api/client'
import type { RankingItem } from '@/types/rs'

export function useCountryRankings(asOf?: string | null) {
  return useQuery<RankingItem[]>({
    queryKey: ['rankings', 'countries', asOf ?? 'live'],
    queryFn: async () => {
      const params = asOf ? { as_of: asOf } : {}
      const response = await apiClient.get<RankingItem[]>('/rankings/countries', { params })
      return response.data
    },
  })
}

export function useSectorRankings(countryCode: string, asOf?: string | null) {
  return useQuery<RankingItem[]>({
    queryKey: ['rankings', 'sectors', countryCode, asOf ?? 'live'],
    queryFn: async () => {
      const params = asOf ? { as_of: asOf } : {}
      const response = await apiClient.get<RankingItem[]>(`/rankings/sectors/${countryCode}`, { params })
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
