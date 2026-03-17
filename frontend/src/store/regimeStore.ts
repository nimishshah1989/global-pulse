import { create } from 'zustand'
import type { Regime } from '@/types/rs'

interface RegimeState {
  regime: Regime
  setRegime: (regime: Regime) => void
}

export const useRegimeStore = create<RegimeState>((set) => ({
  regime: 'RISK_ON',
  setRegime: (regime) => set({ regime }),
}))
