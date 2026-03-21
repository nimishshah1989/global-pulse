import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueries } from '@tanstack/react-query'
import apiClient from '@/api/client'
import { COUNTRY_FLAGS, COUNTRY_NAMES, SECTOR_DISPLAY_NAMES } from '@/data/countryData'
import PeriodSelector from '@/components/common/PeriodSelector'
import type { Period } from '@/components/common/PeriodSelector'
import type { RankingItem } from '@/types/rs'

const COUNTRIES = ['US', 'UK', 'JP', 'HK', 'IN', 'KR', 'CN', 'TW', 'AU', 'BR', 'CA', 'DE', 'FR'] as const
const SECTORS = [
  'technology', 'financials', 'healthcare', 'energy', 'industrials',
  'materials', 'consumer_discretionary', 'consumer_staples',
  'utilities', 'real_estate', 'communication_services',
] as const

function rsScoreColor(score: number): string {
  if (score >= 70) return 'bg-emerald-100 text-emerald-800'
  if (score >= 60) return 'bg-emerald-50 text-emerald-700'
  if (score >= 50) return 'bg-amber-50 text-amber-700'
  if (score >= 40) return 'bg-orange-50 text-orange-700'
  return 'bg-red-50 text-red-700'
}

export default function SectorScanner(): JSX.Element {
  const navigate = useNavigate()
  const [period, setPeriod] = useState<Period>('3m')

  // Fetch sector rankings for each country in parallel
  const countryQueries = useQueries({
    queries: COUNTRIES.map((code) => ({
      queryKey: ['rankings', 'sectors', code, 'live', 'default', period],
      queryFn: async () => {
        const params: Record<string, string> = {}
        if (period) params.period = period
        const response = await apiClient.get<RankingItem[]>(`/rankings/sectors/${code}`, { params })
        return { country: code, sectors: response.data }
      },
    })),
  })

  const isLoading = countryQueries.some((q) => q.isLoading)
  const hasData = countryQueries.some((q) => q.data)

  // Build the matrix: sector -> country -> RS score
  const matrix = new Map<string, Map<string, RankingItem>>()
  for (const query of countryQueries) {
    if (!query.data) continue
    const { country, sectors } = query.data
    for (const item of sectors) {
      const sectorKey = item.sector ?? ''
      if (!matrix.has(sectorKey)) matrix.set(sectorKey, new Map())
      matrix.get(sectorKey)?.set(country, item)
    }
  }

  const handleCellClick = (countryCode: string, sector: string) => {
    navigate(`/compass/country/${countryCode}/sector/${sector}`)
  }

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Sector Scanner</h1>
          <p className="text-sm text-slate-500 mt-1">Cross-country sector comparison — which country's sector is strongest?</p>
        </div>
        <PeriodSelector value={period} onChange={setPeriod} />
      </div>

      {isLoading && (
        <div className="flex items-center justify-center h-64 text-slate-400">Loading sector matrix...</div>
      )}

      {hasData && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider sticky left-0 bg-slate-50 z-10 min-w-[160px]">
                    Sector
                  </th>
                  {COUNTRIES.map((code) => (
                    <th
                      key={code}
                      className="px-2 py-3 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider min-w-[70px]"
                    >
                      <div className="flex flex-col items-center gap-0.5">
                        <span className="text-sm">{COUNTRY_FLAGS[code]}</span>
                        <span>{code}</span>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {SECTORS.map((sector) => {
                  const row = matrix.get(sector)
                  return (
                    <tr key={sector} className="border-b border-slate-50 hover:bg-slate-50/50">
                      <td className="px-4 py-2.5 text-sm font-medium text-slate-900 sticky left-0 bg-white z-10">
                        {SECTOR_DISPLAY_NAMES[sector] ?? sector}
                      </td>
                      {COUNTRIES.map((code) => {
                        const item = row?.get(code)
                        if (!item) {
                          return (
                            <td key={code} className="px-2 py-2.5 text-center">
                              <span className="text-slate-300 text-xs">--</span>
                            </td>
                          )
                        }
                        const colorClass = rsScoreColor(item.rs_score)
                        return (
                          <td key={code} className="px-2 py-2.5 text-center">
                            <button
                              onClick={() => handleCellClick(code, sector)}
                              className={`inline-block rounded-md px-2 py-1 font-mono text-xs font-semibold transition-opacity hover:opacity-80 ${colorClass}`}
                              title={`${COUNTRY_NAMES[code]} ${SECTOR_DISPLAY_NAMES[sector]} — RS: ${item.rs_score.toFixed(1)}`}
                            >
                              {item.rs_score.toFixed(0)}
                            </button>
                          </td>
                        )
                      })}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-4 mt-4 text-xs text-slate-500">
        <span className="font-medium">Score legend:</span>
        <div className="flex items-center gap-1">
          <span className="w-4 h-4 rounded bg-emerald-100" />
          <span>70+</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-4 h-4 rounded bg-emerald-50" />
          <span>60-70</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-4 h-4 rounded bg-amber-50" />
          <span>50-60</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-4 h-4 rounded bg-orange-50" />
          <span>40-50</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-4 h-4 rounded bg-red-50" />
          <span>&lt;40</span>
        </div>
      </div>
    </div>
  )
}
