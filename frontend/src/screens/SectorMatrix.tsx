import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import HeatMapMatrix from '@/components/tables/HeatMapMatrix'
import {
  MATRIX_COUNTRIES,
  MATRIX_SECTORS,
  COUNTRY_LABELS,
  MOCK_COUNTRY_SCORES,
  MOCK_SECTOR_SCORES,
  generateMockMatrix,
} from '@/data/mockMatrixData'

type ViewMode = 'score' | 'quadrant'

export default function SectorMatrix(): JSX.Element {
  const navigate = useNavigate()
  const [mode, setMode] = useState<ViewMode>('score')

  const matrix = useMemo(() => generateMockMatrix(), [])

  function handleCellClick(country: string, sector: string): void {
    const sectorSlug = sector.toLowerCase().replace(/[.\s]+/g, '-')
    navigate(`/compass/country/${country}/sector/${sectorSlug}`)
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          🔀 Sector Matrix
        </h1>
        <p className="text-sm text-slate-500">
          Which country's sector is strongest?
        </p>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => setMode('score')}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
            mode === 'score'
              ? 'bg-teal-600 text-white'
              : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
          }`}
        >
          Score View
        </button>
        <button
          onClick={() => setMode('quadrant')}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
            mode === 'quadrant'
              ? 'bg-teal-600 text-white'
              : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
          }`}
        >
          Quadrant View
        </button>
      </div>

      <HeatMapMatrix
        countries={[...MATRIX_COUNTRIES]}
        sectors={[...MATRIX_SECTORS]}
        matrix={matrix}
        mode={mode}
        onCellClick={handleCellClick}
        countryLabels={COUNTRY_LABELS}
        countryScores={MOCK_COUNTRY_SCORES}
        sectorScores={MOCK_SECTOR_SCORES}
      />
    </div>
  )
}
