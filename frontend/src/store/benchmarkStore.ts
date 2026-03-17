import { create } from 'zustand'

interface BenchmarkState {
  benchmark: string
  setBenchmark: (benchmark: string) => void
}

export const useBenchmarkStore = create<BenchmarkState>((set) => ({
  benchmark: 'ACWI',
  setBenchmark: (benchmark) => set({ benchmark }),
}))
