import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import WorldChoropleth from '@/components/maps/WorldChoropleth'
import RSRankingTable from '@/components/tables/RSRankingTable'
import TopBottomStrip from '@/components/common/TopBottomStrip'
import RegimeBanner from '@/components/common/RegimeBanner'
import LoadingSkeleton from '@/components/common/LoadingSkeleton'
import ErrorAlert from '@/components/common/ErrorAlert'
import { useCountryRankings } from '@/api/hooks/useRankings'
import { useRegime } from '@/api/hooks/useRegime'
import { MOCK_COUNTRY_DATA } from '@/data/mockCountryData'
import type { RankingItem } from '@/types/rs'

export default function GlobalPulse(): JSX.Element {
  const navigate = useNavigate()
  const { data: countryData, isLoading: countriesLoading, error: countriesError, refetch: refetchCountries } = useCountryRankings()
  const { data: regimeData } = useRegime()

  const rankings = countryData ?? MOCK_COUNTRY_DATA

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

      {regimeData && (
        <RegimeBanner regime={regimeData.regime} />
      )}

      {countriesError && (
        <ErrorAlert
          message={countriesError instanceof Error ? countriesError.message : 'Unknown error'}
          onRetry={() => void refetchCountries()}
        />
      )}

      {countriesLoading ? (
        <LoadingSkeleton type="chart" />
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <WorldChoropleth data={rankings} />
        </div>
      )}

      {countriesLoading ? (
        <LoadingSkeleton type="table" rows={3} />
      ) : (
        <TopBottomStrip data={rankings} />
      )}

      <div>
        <h2 className="mb-3 text-lg font-semibold text-slate-800">
          Country RS Rankings
        </h2>
        {countriesLoading ? (
          <LoadingSkeleton type="table" rows={10} />
        ) : (
          <RSRankingTable
            data={rankings}
            onRowClick={handleRowClick}
            showCountry
          />
        )}
      </div>
    </div>
  )
}
