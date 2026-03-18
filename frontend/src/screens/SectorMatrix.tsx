import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import HeatMapMatrix from '@/components/tables/HeatMapMatrix'
import LoadingSkeleton from '@/components/common/LoadingSkeleton'
import ErrorAlert from '@/components/common/ErrorAlert'
import { useMatrix } from '@/api/hooks/useMatrix'
import type { MatrixData } from '@/api/hooks/useMatrix'
import type { Action } from '@/types/rs'
import {
  MATRIX_COUNTRIES,
  MATRIX_SECTORS,
  COUNTRY_LABELS,
  MOCK_COUNTRY_SCORES,
  MOCK_SECTOR_SCORES,
  generateMockMatrix,
} from '@/data/mockMatrixData'
import type { MatrixCellData } from '@/data/mockMatrixData'

type ViewMode = 'score' | 'action'

function getActionFromScore(score: number): Action {
  if (score > 70) return 'BUY'
  if (score > 60) return 'ACCUMULATE'
  if (score > 50) return 'HOLD_FADING'
  if (score > 40) return 'WATCH'
  if (score > 30) return 'REDUCE'
  return 'SELL'
}

function transformApiMatrix(apiData: MatrixData): {
  countries: string[]
  sectors: string[]
  matrix: Record<string, Record<string, MatrixCellData>>
  countryLabels: Record<string, string>
  countryScores: Record<string, number>
  sectorScores: Record<string, number>
} {
  const matrix: Record<string, Record<string, MatrixCellData>> = {}
  for (const cell of apiData.cells) {
    if (!matrix[cell.country]) {
      matrix[cell.country] = {}
    }
    const action = (cell.action as Action) ?? getActionFromScore(cell.rs_score)
    matrix[cell.country][cell.sector] = {
      score: cell.rs_score,
      quadrant: action,
    }
  }

  return {
    countries: apiData.countries,
    sectors: apiData.sectors,
    matrix,
    countryLabels: COUNTRY_LABELS,
    countryScores: apiData.country_scores,
    sectorScores: apiData.sector_scores,
  }
}

export default function SectorMatrix(): JSX.Element {
  const navigate = useNavigate()
  const [mode, setMode] = useState<ViewMode>('score')

  const { data: apiData, isLoading, error, refetch } = useMatrix()

  const mockMatrix = useMemo(() => generateMockMatrix(), [])

  const {
    countries,
    sectors,
    matrix,
    countryLabels,
    countryScores,
    sectorScores,
  } = useMemo(() => {
    if (apiData) {
      return transformApiMatrix(apiData)
    }
    return {
      countries: [...MATRIX_COUNTRIES],
      sectors: [...MATRIX_SECTORS],
      matrix: mockMatrix,
      countryLabels: COUNTRY_LABELS,
      countryScores: MOCK_COUNTRY_SCORES,
      sectorScores: MOCK_SECTOR_SCORES,
    }
  }, [apiData, mockMatrix])

  function handleCellClick(country: string, sector: string): void {
    const sectorSlug = sector.toLowerCase().replace(/[.\s]+/g, '-')
    navigate(`/compass/country/${country}/sector/${sectorSlug}`)
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          Sector Matrix
        </h1>
        <p className="text-sm text-slate-500">
          Which country's sector is strongest?
        </p>
      </div>

      {error && (
        <ErrorAlert
          message={error instanceof Error ? error.message : 'Unknown error'}
          onRetry={() => void refetch()}
        />
      )}

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
          onClick={() => setMode('action')}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
            mode === 'action'
              ? 'bg-teal-600 text-white'
              : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
          }`}
        >
          Action View
        </button>
      </div>

      {/* Action color legend */}
      {mode === 'action' && (
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <span className="font-semibold text-slate-500">Legend:</span>
          {ACTION_LEGEND.map((item) => (
            <span key={item.label} className="flex items-center gap-1">
              <span className={`inline-block h-3 w-3 rounded ${item.color}`} />
              <span className="text-slate-600">{item.label}</span>
            </span>
          ))}
        </div>
      )}

      {isLoading ? (
        <LoadingSkeleton type="table" rows={11} />
      ) : (
        <HeatMapMatrix
          countries={countries}
          sectors={sectors}
          matrix={matrix}
          mode={mode === 'action' ? 'quadrant' : 'score'}
          onCellClick={handleCellClick}
          countryLabels={countryLabels}
          countryScores={countryScores}
          sectorScores={sectorScores}
        />
      )}
    </div>
  )
}

const ACTION_LEGEND = [
  { label: 'Buy', color: 'bg-emerald-500' },
  { label: 'Accumulate', color: 'bg-teal-500' },
  { label: 'Hold', color: 'bg-yellow-400' },
  { label: 'Watch', color: 'bg-blue-500' },
  { label: 'Reduce', color: 'bg-orange-500' },
  { label: 'Sell', color: 'bg-red-500' },
  { label: 'Avoid', color: 'bg-slate-400' },
]
