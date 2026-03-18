import { useQuery } from '@tanstack/react-query'
import apiClient from '@/api/client'

export interface PricePoint {
  instrument_id: string
  date: string
  open: number | null
  high: number | null
  low: number | null
  close: number
  volume: number | null
}

export interface RSLinePoint {
  date: string
  rs_line: number
  rs_ma_150: number
  volume: number
}

export function useInstrumentPrices(instrumentId: string, limit = 365) {
  return useQuery<PricePoint[]>({
    queryKey: ['instrument', 'prices', instrumentId, limit],
    queryFn: async () => {
      const response = await apiClient.get<PricePoint[]>(
        `/instruments/${instrumentId}/prices`,
        { params: { limit } },
      )
      return response.data
    },
    enabled: !!instrumentId,
  })
}

/**
 * Compute RS line data from two price series (asset vs benchmark).
 * Returns data suitable for the RSLineChart component.
 */
export function computeRSLineFromPrices(
  assetPrices: PricePoint[],
  benchmarkPrices: PricePoint[],
): RSLinePoint[] {
  const benchMap = new Map<string, number>()
  for (const p of benchmarkPrices) {
    benchMap.set(p.date, p.close)
  }

  const rsPoints: RSLinePoint[] = []
  let firstRatio: number | null = null

  for (const p of assetPrices) {
    const benchClose = benchMap.get(p.date)
    if (benchClose == null || benchClose === 0) continue

    const rawRatio = (p.close / benchClose) * 100
    if (firstRatio === null) firstRatio = rawRatio
    const normalizedRS = firstRatio === 0 ? 100 : (rawRatio / firstRatio) * 100

    rsPoints.push({
      date: p.date,
      rs_line: Math.round(normalizedRS * 100) / 100,
      rs_ma_150: 100, // Will be computed below
      volume: p.volume ?? 0,
    })
  }

  // Compute 150-day SMA of RS line
  for (let i = 0; i < rsPoints.length; i++) {
    const start = Math.max(0, i - 149)
    const window = rsPoints.slice(start, i + 1)
    const sum = window.reduce((acc, pt) => acc + pt.rs_line, 0)
    rsPoints[i].rs_ma_150 = Math.round((sum / window.length) * 100) / 100
  }

  return rsPoints
}
