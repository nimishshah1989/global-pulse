import { useQuery } from '@tanstack/react-query'
import apiClient from '@/api/client'
import type { RankingItem } from '@/types/rs'

export function useCountryRankings(asOf?: string | null, benchmark?: string | null) {
  return useQuery<RankingItem[]>({
    queryKey: ['rankings', 'countries', asOf ?? 'live', benchmark ?? 'default'],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (asOf) params.as_of = asOf
      if (benchmark) params.benchmark = benchmark
      const response = await apiClient.get<RankingItem[]>('/rankings/countries', { params })
      return response.data
    },
  })
}

export function useSectorRankings(countryCode: string, asOf?: string | null, benchmark?: string | null) {
  return useQuery<RankingItem[]>({
    queryKey: ['rankings', 'sectors', countryCode, asOf ?? 'live', benchmark ?? 'default'],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (asOf) params.as_of = asOf
      if (benchmark) params.benchmark = benchmark
      const response = await apiClient.get<RankingItem[]>(`/rankings/sectors/${countryCode}`, { params })
      return response.data
    },
    enabled: !!countryCode,
  })
}

export function useStockRankings(countryCode: string, sector: string, benchmark?: string | null) {
  return useQuery<RankingItem[]>({
    queryKey: ['rankings', 'stocks', countryCode, sector, benchmark ?? 'default'],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (benchmark) params.benchmark = benchmark
      const response = await apiClient.get<RankingItem[]>(
        `/rankings/stocks/${countryCode}/${sector}`,
        { params },
      )
      return response.data
    },
    enabled: !!countryCode && !!sector,
  })
}

export function useGlobalSectorRankings(benchmark?: string | null) {
  return useQuery<RankingItem[]>({
    queryKey: ['rankings', 'global-sectors', benchmark ?? 'default'],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (benchmark) params.benchmark = benchmark
      const response = await apiClient.get<RankingItem[]>('/rankings/global-sectors', { params })
      return response.data
    },
  })
}

export function useTopETFs(
  action?: string,
  country?: string,
  sector?: string,
  limit: number = 50,
) {
  return useQuery<RankingItem[]>({
    queryKey: ['rankings', 'etfs', 'top', action, country, sector, limit],
    queryFn: async () => {
      const params: Record<string, string | number> = { limit }
      if (action) params.action = action
      if (country) params.country = country
      if (sector) params.sector = sector
      const response = await apiClient.get<RankingItem[]>('/rankings/etfs/top', { params })
      return response.data
    },
  })
}
