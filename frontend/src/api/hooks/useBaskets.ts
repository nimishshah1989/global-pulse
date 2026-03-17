import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/api/client'
import type { Basket, BasketPosition } from '@/types/baskets'

export function useBaskets() {
  return useQuery<Basket[]>({
    queryKey: ['baskets'],
    queryFn: async () => {
      const response = await apiClient.get<Basket[]>('/baskets')
      return response.data
    },
  })
}

export function useBasket(id: string) {
  return useQuery<Basket>({
    queryKey: ['baskets', id],
    queryFn: async () => {
      const response = await apiClient.get<Basket>(`/baskets/${id}`)
      return response.data
    },
    enabled: !!id,
  })
}

interface CreateBasketInput {
  name: string
  description?: string
  benchmark_id?: string
  weighting_method?: 'equal' | 'manual' | 'rs_weighted'
}

export function useCreateBasket() {
  const queryClient = useQueryClient()

  return useMutation<Basket, Error, CreateBasketInput>({
    mutationFn: async (input) => {
      const response = await apiClient.post<Basket>('/baskets', input)
      return response.data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['baskets'] })
    },
  })
}

interface AddPositionInput {
  basketId: string
  instrument_id: string
  weight: number
}

export function useAddPosition() {
  const queryClient = useQueryClient()

  return useMutation<BasketPosition, Error, AddPositionInput>({
    mutationFn: async ({ basketId, ...data }) => {
      const response = await apiClient.post<BasketPosition>(
        `/baskets/${basketId}/positions`,
        data,
      )
      return response.data
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ['baskets', variables.basketId] })
    },
  })
}

interface RemovePositionInput {
  basketId: string
  positionId: string
}

export function useRemovePosition() {
  const queryClient = useQueryClient()

  return useMutation<void, Error, RemovePositionInput>({
    mutationFn: async ({ basketId, positionId }) => {
      await apiClient.delete(`/baskets/${basketId}/positions/${positionId}`)
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ['baskets', variables.basketId] })
    },
  })
}
