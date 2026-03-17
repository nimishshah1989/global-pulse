import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import WorldChoropleth from '@/components/maps/WorldChoropleth'
import RSRankingTable from '@/components/tables/RSRankingTable'
import TopBottomStrip from '@/components/common/TopBottomStrip'
import { MOCK_COUNTRY_DATA } from '@/data/mockCountryData'
import type { RankingItem } from '@/types/rs'

export default function GlobalPulse(): JSX.Element {
  const navigate = useNavigate()

  const handleRowClick = useCallback(
    (item: RankingItem) => {
      if (item.country) {
        navigate(`/compass/country/${item.country}`)
      }
    },
    [navigate],
  )

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">
        Global Pulse
      </h1>

      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <WorldChoropleth data={MOCK_COUNTRY_DATA} />
      </div>

      <TopBottomStrip data={MOCK_COUNTRY_DATA} />

      <div>
        <h2 className="mb-3 text-lg font-semibold text-slate-800">
          Country RS Rankings
        </h2>
        <RSRankingTable
          data={MOCK_COUNTRY_DATA}
          onRowClick={handleRowClick}
          showCountry
        />
      </div>
    </div>
  )
}
