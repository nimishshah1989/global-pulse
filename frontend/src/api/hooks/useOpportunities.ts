import { useQuery } from '@tanstack/react-query'
import apiClient from '@/api/client'
import type { Opportunity, SignalType } from '@/types/opportunities'

interface OpportunityFilters {
  signal_type?: SignalType
  hierarchy_level?: number
  min_conviction?: number
  liquidity_tier?: number
}

export function useOpportunities(filters?: OpportunityFilters) {
  return useQuery<Opportunity[]>({
    queryKey: ['opportunities', filters],
    queryFn: async () => {
      const response = await apiClient.get<Opportunity[]>('/opportunities', {
        params: filters,
      })
      return response.data
    },
  })
}

export function useMultiLevelAlignments() {
  return useQuery<Opportunity[]>({
    queryKey: ['opportunities', 'multi-level'],
    queryFn: async () => {
      const response = await apiClient.get<Opportunity[]>('/opportunities/multi-level')
      return response.data
    },
  })
}
