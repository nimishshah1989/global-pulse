import type { Quadrant } from '@/types/rs'

export interface HeatMapCellData {
  score: number
  quadrant: Quadrant
}

interface HeatMapMatrixProps {
  countries: string[]
  sectors: string[]
  matrix: Record<string, Record<string, HeatMapCellData>>
  mode: 'score' | 'quadrant'
  onCellClick: (country: string, sector: string) => void
  countryLabels?: Record<string, string>
  countryScores?: Record<string, number>
  sectorScores?: Record<string, number>
}

function getScoreColor(score: number): string {
  if (score >= 70) return 'bg-emerald-500 text-white'
  if (score >= 60) return 'bg-emerald-300 text-emerald-900'
  if (score >= 50) return 'bg-emerald-100 text-emerald-800'
  if (score >= 40) return 'bg-amber-100 text-amber-800'
  if (score >= 30) return 'bg-amber-300 text-amber-900'
  return 'bg-red-400 text-white'
}

const QUADRANT_CELL_STYLES: Record<Quadrant, string> = {
  LEADING: 'bg-emerald-100 text-emerald-800',
  WEAKENING: 'bg-amber-100 text-amber-800',
  LAGGING: 'bg-red-100 text-red-800',
  IMPROVING: 'bg-blue-100 text-blue-800',
}

const QUADRANT_SHORT: Record<Quadrant, string> = {
  LEADING: 'L',
  WEAKENING: 'W',
  LAGGING: 'Lg',
  IMPROVING: 'I',
}

export default function HeatMapMatrix({
  countries,
  sectors,
  matrix,
  mode,
  onCellClick,
  countryLabels,
  countryScores,
  sectorScores,
}: HeatMapMatrixProps): JSX.Element {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white" data-testid="heatmap-matrix">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50">
            <th className="sticky left-0 z-20 bg-slate-50 px-3 py-2 text-left font-semibold text-slate-500">
              Sector
            </th>
            {sectorScores && (
              <th className="px-2 py-2 text-center font-semibold text-slate-500">Global</th>
            )}
            {countries.map((country) => (
              <th key={country} className="px-2 py-2 text-center font-semibold text-slate-700">
                <div>{countryLabels?.[country] ?? country}</div>
                {countryScores && (
                  <div className="mt-0.5 font-mono text-[10px] text-slate-400">
                    {countryScores[country]?.toFixed(0) ?? '-'}
                  </div>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {sectors.map((sector) => (
            <tr key={sector} className="group">
              <td className="sticky left-0 z-10 bg-white px-3 py-2 font-medium text-slate-900 group-hover:bg-slate-50">
                {sector}
              </td>
              {sectorScores && (
                <td className="px-2 py-2 text-center group-hover:bg-slate-50">
                  <span className="font-mono font-semibold text-slate-600">
                    {sectorScores[sector]?.toFixed(0) ?? '-'}
                  </span>
                </td>
              )}
              {countries.map((country) => {
                const cell = matrix[country]?.[sector]
                if (!cell) {
                  return (
                    <td key={country} className="px-2 py-2 text-center text-slate-300 group-hover:bg-slate-50">
                      -
                    </td>
                  )
                }

                const cellStyle =
                  mode === 'score'
                    ? getScoreColor(cell.score)
                    : QUADRANT_CELL_STYLES[cell.quadrant]

                const cellText =
                  mode === 'score'
                    ? cell.score.toFixed(0)
                    : QUADRANT_SHORT[cell.quadrant]

                return (
                  <td
                    key={country}
                    onClick={() => onCellClick(country, sector)}
                    className="cursor-pointer px-1 py-1 text-center group-hover:bg-slate-50"
                    data-testid={`cell-${country}-${sector}`}
                  >
                    <span
                      className={`inline-block min-w-[2rem] rounded px-1.5 py-1 font-mono font-semibold ${cellStyle}`}
                    >
                      {cellText}
                    </span>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
