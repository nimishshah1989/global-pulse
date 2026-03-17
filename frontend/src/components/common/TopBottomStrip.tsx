import type { RankingItem } from '@/types/rs'
import { COUNTRY_FLAGS, COUNTRY_NAMES } from '@/data/mockCountryData'

interface TopBottomStripProps {
  data: RankingItem[]
}

export default function TopBottomStrip({ data }: TopBottomStripProps): JSX.Element {
  const sorted = [...data].sort((a, b) => b.adjusted_rs_score - a.adjusted_rs_score)
  const top5 = sorted.slice(0, 5)
  const bottom5 = sorted.slice(-5).reverse()

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:gap-0">
      <div className="flex flex-1 items-center gap-3 rounded-l-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-emerald-700">
          Strongest
        </span>
        <div className="flex flex-1 items-center gap-4 overflow-x-auto">
          {top5.map((item) => {
            const code = item.country ?? ''
            return (
              <div key={item.instrument_id} className="flex items-center gap-1.5 whitespace-nowrap">
                <span className="text-sm">{COUNTRY_FLAGS[code] ?? ''}</span>
                <span className="text-xs font-medium text-emerald-800">
                  {COUNTRY_NAMES[code] ?? code}
                </span>
                <span className="font-mono text-xs font-semibold text-emerald-700">
                  {item.adjusted_rs_score.toFixed(1)}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      <div className="flex flex-1 items-center gap-3 rounded-r-xl border border-red-200 bg-red-50 px-4 py-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-red-700">
          Weakest
        </span>
        <div className="flex flex-1 items-center gap-4 overflow-x-auto">
          {bottom5.map((item) => {
            const code = item.country ?? ''
            return (
              <div key={item.instrument_id} className="flex items-center gap-1.5 whitespace-nowrap">
                <span className="text-sm">{COUNTRY_FLAGS[code] ?? ''}</span>
                <span className="text-xs font-medium text-red-800">
                  {COUNTRY_NAMES[code] ?? code}
                </span>
                <span className="font-mono text-xs font-semibold text-red-700">
                  {item.adjusted_rs_score.toFixed(1)}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
