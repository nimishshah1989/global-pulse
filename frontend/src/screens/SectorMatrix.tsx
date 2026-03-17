import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import HeatMapMatrix from '@/components/tables/HeatMapMatrix'
import LoadingSkeleton from '@/components/common/LoadingSkeleton'
import ErrorAlert from '@/components/common/ErrorAlert'
import { useMatrix } from '@/api/hooks/useMatrix'
import type { MatrixData } from '@/api/hooks/useMatrix'
import type { Quadrant } from '@/types/rs'
import {
  MATRIX_COUNTRIES,
  MATRIX_SECTORS,
  COUNTRY_LABELS,
  MOCK_COUNTRY_SCORES,
  MOCK_SECTOR_SCORES,
  generateMockMatrix,
} from '@/data/mockMatrixData'
import type { MatrixCellData } from '@/data/mockMatrixData'

type ViewMode = 'score' | 'quadrant'

function getQuadrantFromScoreAndMomentum(score: number): Quadrant {
  // When we only have a score from the API, approximate the quadrant
  if (score > 60) return 'LEADING'
  if (score > 50) return 'WEAKENING'
  if (score > 35) return 'IMPROVING'
  return 'LAGGING'
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
    matrix[cell.country][cell.sector] = {
      score: cell.adjusted_rs_score,
      quadrant: (cell.quadrant as Quadrant) ?? getQuadrantFromScoreAndMomentum(cell.adjusted_rs_score),
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
          🔀 Sector Matrix
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

      {isLoading ? (
        <LoadingSkeleton type="table" rows={11} />
      ) : (
        <HeatMapMatrix
          countries={countries}
          sectors={sectors}
          matrix={matrix}
          mode={mode}
          onCellClick={handleCellClick}
          countryLabels={countryLabels}
          countryScores={countryScores}
          sectorScores={sectorScores}
        />
      )}
    </div>
  )
}
