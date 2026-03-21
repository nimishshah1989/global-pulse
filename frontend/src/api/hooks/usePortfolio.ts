import { useQuery } from '@tanstack/react-query'
import apiClient from '@/api/client'

export function useModelPortfolio(portfolioType: string = 'etf_only', country?: string) {
  return useQuery({
    queryKey: ['portfolio', 'model', portfolioType, country ?? 'all'],
    queryFn: async () => {
      const params: Record<string, string> = { portfolio_type: portfolioType }
      if (country) params.country = country
      const response = await apiClient.get('/portfolio/model', { params })
      return response.data
    },
    retry: false,
  })
}

export function useOpportunities(signalType?: string, limit: number = 100) {
  return useQuery({
    queryKey: ['opportunities', signalType ?? 'all', limit],
    queryFn: async () => {
      const params: Record<string, string | number> = { limit }
      if (signalType) params.signal_type = signalType
      const response = await apiClient.get('/opportunities', { params })
      return response.data
    },
    retry: false,
  })
}
