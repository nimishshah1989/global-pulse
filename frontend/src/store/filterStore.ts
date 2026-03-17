import { create } from 'zustand'
import type { Quadrant } from '@/types/rs'

interface FilterState {
  quadrantFilter: Quadrant | null
  liquidityFilter: number | null
  rsThreshold: number
  setQuadrantFilter: (quadrant: Quadrant | null) => void
  setLiquidityFilter: (tier: number | null) => void
  setRsThreshold: (value: number) => void
  resetFilters: () => void
}

export const useFilterStore = create<FilterState>((set) => ({
  quadrantFilter: null,
  liquidityFilter: null,
  rsThreshold: 0,
  setQuadrantFilter: (quadrant) => set({ quadrantFilter: quadrant }),
  setLiquidityFilter: (tier) => set({ liquidityFilter: tier }),
  setRsThreshold: (value) => set({ rsThreshold: value }),
  resetFilters: () =>
    set({
      quadrantFilter: null,
      liquidityFilter: null,
      rsThreshold: 0,
    }),
}))
