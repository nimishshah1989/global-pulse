import { useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import RRGScatter from '@/components/charts/RRGScatter'
import RSRankingTable from '@/components/tables/RSRankingTable'
import RSLineChart from '@/components/charts/RSLineChart'
import RegimeBanner from '@/components/common/RegimeBanner'
import LoadingSkeleton from '@/components/common/LoadingSkeleton'
import ErrorAlert from '@/components/common/ErrorAlert'
import { useSectorRankings } from '@/api/hooks/useRankings'
import { useSectorRRG } from '@/api/hooks/useRRG'
import { useRegime } from '@/api/hooks/useRegime'
import { MOCK_SECTOR_DATA, getMockRRGData, getMockRSLineData } from '@/data/mockSectorData'
import { COUNTRY_NAMES } from '@/data/mockCountryData'
import type { RankingItem } from '@/types/rs'

export default function CountryDeepDive(): JSX.Element {
  const { countryCode } = useParams<{ countryCode: string }>()
  const navigate = useNavigate()
  const code = countryCode ?? 'US'

  const { data: sectorData, isLoading: sectorsLoading, error: sectorsError, refetch: refetchSectors } = useSectorRankings(code)
  const { data: rrgApiData, isLoading: rrgLoading } = useSectorRRG(code)
  const { data: regimeData } = useRegime()

  const countryName = COUNTRY_NAMES[code] ?? code

  const mockSectors = MOCK_SECTOR_DATA[code] ?? MOCK_SECTOR_DATA['US'] ?? []
  const sectors = sectorData ?? mockSectors
  const rrgData = rrgApiData ?? getMockRRGData(code in MOCK_SECTOR_DATA ? code : 'US')
  const rsLineData = getMockRSLineData()

  const [selectedSector, setSelectedSector] = useState<string>(
    sectors[0]?.name ?? '',
  )

  const handleSectorSelect = useCallback(
    (item: RankingItem) => {
      setSelectedSector(item.name)
    },
    [],
  )

  const handleRRGPointClick = useCallback(
    (id: string) => {
      const sector = sectors.find((s) => s.instrument_id === id)
      if (sector?.sector) {
        navigate(`/compass/country/${code}/sector/${sector.sector}`)
      }
    },
    [navigate, code, sectors],
  )

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">
        {countryName} — Sector Rotation
      </h1>

      {regimeData && (
        <RegimeBanner regime={regimeData.regime} />
      )}

      {sectorsError && (
        <ErrorAlert
          message={sectorsError instanceof Error ? sectorsError.message : 'Unknown error'}
          onRetry={() => void refetchSectors()}
        />
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">
            Sector Rankings
          </h2>
          {sectorsLoading ? (
            <LoadingSkeleton type="table" rows={8} />
          ) : (
            <RSRankingTable
              data={sectors}
              onRowClick={handleSectorSelect}
              showSector
            />
          )}
        </div>

        <div className="lg:col-span-3">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">
            Relative Rotation Graph
          </h2>
          {rrgLoading ? (
            <LoadingSkeleton type="chart" />
          ) : (
            <RRGScatter
              data={rrgData}
              width={580}
              height={450}
              onPointClick={handleRRGPointClick}
            />
          )}
        </div>
      </div>

      <div>
        <RSLineChart
          data={rsLineData}
          title={`RS Line — ${selectedSector || 'Select a sector'} vs ${countryName} Index`}
        />
        <p className="mt-2 text-xs text-slate-400">
          Click a sector row to view its RS line. Click a sector in the RRG chart to navigate to stock selection.
        </p>
      </div>
    </div>
  )
}
