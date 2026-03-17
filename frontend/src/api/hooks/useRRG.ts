import { useQuery } from '@tanstack/react-query'
import apiClient from '@/api/client'
import type { RRGDataPoint } from '@/types/rs'

export function useCountryRRG() {
  return useQuery<RRGDataPoint[]>({
    queryKey: ['rrg', 'countries'],
    queryFn: async () => {
      const response = await apiClient.get<RRGDataPoint[]>('/rrg/countries')
      return response.data
    },
  })
}

export function useSectorRRG(countryCode: string) {
  return useQuery<RRGDataPoint[]>({
    queryKey: ['rrg', 'sectors', countryCode],
    queryFn: async () => {
      const response = await apiClient.get<RRGDataPoint[]>(`/rrg/sectors/${countryCode}`)
      return response.data
    },
    enabled: !!countryCode,
  })
}

export function useStockRRG(countryCode: string, sector: string) {
  return useQuery<RRGDataPoint[]>({
    queryKey: ['rrg', 'stocks', countryCode, sector],
    queryFn: async () => {
      const response = await apiClient.get<RRGDataPoint[]>(
        `/rrg/stocks/${countryCode}/${sector}`,
      )
      return response.data
    },
    enabled: !!countryCode && !!sector,
  })
}
