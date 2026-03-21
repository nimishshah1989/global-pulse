import { useQuery } from '@tanstack/react-query'
import apiClient from '@/api/client'
import type { RankingItem } from '@/types/rs'

export function useCountryRankings(
  asOf?: string | null,
  benchmark?: string | null,
  period?: string,
) {
  return useQuery<RankingItem[]>({
    queryKey: ['rankings', 'countries', asOf ?? 'live', benchmark ?? 'default', period ?? '3m'],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (asOf) params.as_of = asOf
      if (benchmark) params.benchmark = benchmark
      if (period) params.period = period
      const response = await apiClient.get<RankingItem[]>('/rankings/countries', { params })
      return response.data
    },
  })
}

export function useSectorRankings(
  countryCode: string,
  asOf?: string | null,
  benchmark?: string | null,
  period?: string,
) {
  return useQuery<RankingItem[]>({
    queryKey: ['rankings', 'sectors', countryCode, asOf ?? 'live', benchmark ?? 'default', period ?? '3m'],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (asOf) params.as_of = asOf
      if (benchmark) params.benchmark = benchmark
      if (period) params.period = period
      const response = await apiClient.get<RankingItem[]>(`/rankings/sectors/${countryCode}`, { params })
      return response.data
    },
    enabled: !!countryCode,
  })
}

export function useStockRankings(
  countryCode: string,
  sector: string,
  benchmark?: string | null,
  period?: string,
) {
  return useQuery<RankingItem[]>({
    queryKey: ['rankings', 'stocks', countryCode, sector, benchmark ?? 'default', period ?? '3m'],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (benchmark) params.benchmark = benchmark
      if (period) params.period = period
      const response = await apiClient.get<RankingItem[]>(
        `/rankings/stocks/${countryCode}/${sector}`,
        { params },
      )
      return response.data
    },
    enabled: !!countryCode && !!sector,
  })
}

export function useGlobalSectorRankings(benchmark?: string | null, period?: string) {
  return useQuery<RankingItem[]>({
    queryKey: ['rankings', 'global-sectors', benchmark ?? 'default', period ?? '3m'],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (benchmark) params.benchmark = benchmark
      if (period) params.period = period
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
  period?: string,
) {
  return useQuery<RankingItem[]>({
    queryKey: ['rankings', 'etfs', 'top', action, country, sector, limit, period ?? '3m'],
    queryFn: async () => {
      const params: Record<string, string | number> = { limit }
      if (action) params.action = action
      if (country) params.country = country
      if (sector) params.sector = sector
      if (period) params.period = period
      const response = await apiClient.get<RankingItem[]>('/rankings/etfs/top', { params })
      return response.data
    },
  })
}
