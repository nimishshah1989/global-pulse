import { useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import RRGScatter from '@/components/charts/RRGScatter'
import RSRankingTable from '@/components/tables/RSRankingTable'
import RSLineChart from '@/components/charts/RSLineChart'
import { MOCK_SECTOR_DATA, getMockRRGData, getMockRSLineData } from '@/data/mockSectorData'
import { COUNTRY_NAMES } from '@/data/mockCountryData'
import type { RankingItem } from '@/types/rs'

export default function CountryDeepDive(): JSX.Element {
  const { countryCode } = useParams<{ countryCode: string }>()
  const navigate = useNavigate()
  const code = countryCode ?? 'US'

  const countryName = COUNTRY_NAMES[code] ?? code
  const sectors = MOCK_SECTOR_DATA[code] ?? MOCK_SECTOR_DATA['US'] ?? []
  const rrgData = getMockRRGData(code in MOCK_SECTOR_DATA ? code : 'US')
  const rsLineData = getMockRSLineData()

  const [selectedSector, setSelectedSector] = useState<string>(
    sectors[0]?.name ?? '',
  )

  const handleRowClick = useCallback(
    (item: RankingItem) => {
      if (item.sector) {
        navigate(`/compass/country/${code}/sector/${item.sector}`)
      }
    },
    [navigate, code],
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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">
            Sector Rankings
          </h2>
          <RSRankingTable
            data={sectors}
            onRowClick={handleSectorSelect}
            showSector
          />
        </div>

        <div className="lg:col-span-3">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">
            Relative Rotation Graph
          </h2>
          <RRGScatter
            data={rrgData}
            width={580}
            height={450}
            onPointClick={handleRRGPointClick}
          />
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
