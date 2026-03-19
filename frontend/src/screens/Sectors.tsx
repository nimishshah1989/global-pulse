import { useNavigate, useParams, Link } from 'react-router-dom'
import { useSectorRankings, useCountryRankings } from '@/api/hooks/useRankings'
import { COUNTRY_FLAGS, COUNTRY_NAMES, SECTOR_DISPLAY_NAMES } from '@/data/countryData'
import { formatPercent } from '@/utils/format'
import type { RankingItem, Action } from '@/types/rs'

const ACTION_COLORS: Record<Action, string> = {
  BUY: 'bg-emerald-100 text-emerald-700',
  ACCUMULATE: 'bg-teal-100 text-teal-700',
  HOLD_DIVERGENCE: 'bg-yellow-100 text-yellow-700',
  HOLD_FADING: 'bg-yellow-100 text-yellow-700',
  WATCH: 'bg-blue-100 text-blue-700',
  REDUCE: 'bg-orange-100 text-orange-700',
  SELL: 'bg-red-100 text-red-700',
  AVOID: 'bg-slate-200 text-slate-600',
}

const ACTION_LABELS: Record<Action, string> = {
  BUY: 'Buy',
  ACCUMULATE: 'Accumulate',
  HOLD_DIVERGENCE: 'Hold',
  HOLD_FADING: 'Hold',
  WATCH: 'Watch',
  REDUCE: 'Reduce',
  SELL: 'Sell',
  AVOID: 'Avoid',
}

function ReturnCell({ value }: { value: number | null | undefined }): JSX.Element {
  if (value == null) return <td className="px-3 py-3 text-center text-slate-300 font-mono text-sm">--</td>
  const color = value > 0 ? 'text-emerald-600' : value < 0 ? 'text-red-600' : 'text-slate-500'
  return <td className={`px-3 py-3 text-center font-mono text-sm ${color}`}>{formatPercent(value)}</td>
}

function ActionBadge({ action }: { action: Action }): JSX.Element {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${ACTION_COLORS[action]}`}>
      {ACTION_LABELS[action]}
    </span>
  )
}

function SectorRow({ item, onClick }: { item: RankingItem; onClick: () => void }): JSX.Element {
  const sectorName = SECTOR_DISPLAY_NAMES[item.sector ?? ''] ?? item.sector ?? item.name

  return (
    <tr
      className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
      onClick={onClick}
    >
      <td className="px-4 py-3">
        <div className="text-sm font-semibold text-slate-900">{sectorName}</div>
        <div className="text-xs text-slate-400 font-mono">{item.instrument_id}</div>
      </td>
      <td className="px-3 py-3 text-center"><ActionBadge action={item.action} /></td>
      <td className="px-3 py-3 text-center font-mono text-sm font-semibold text-slate-700">
        {item.rs_score?.toFixed(1)}
      </td>
      <td className="px-3 py-3 text-center text-xs">
        <span className={item.price_trend === 'OUTPERFORMING' ? 'text-emerald-600' : 'text-red-500'}>
          {item.price_trend === 'OUTPERFORMING' ? 'Outperforming' : 'Underperforming'}
        </span>
      </td>
      <td className="px-3 py-3 text-center text-xs">
        <span className={item.volume_character === 'ACCUMULATION' ? 'text-emerald-600' : item.volume_character === 'DISTRIBUTION' ? 'text-red-500' : 'text-slate-500'}>
          {item.volume_character === 'ACCUMULATION' ? 'Accumulation' : item.volume_character === 'DISTRIBUTION' ? 'Distribution' : 'Neutral'}
        </span>
      </td>
      <ReturnCell value={item.return_1m} />
      <ReturnCell value={item.return_3m} />
      <ReturnCell value={item.return_6m} />
      <ReturnCell value={item.return_12m} />
      <ReturnCell value={item.excess_3m} />
      <ReturnCell value={item.excess_6m} />
    </tr>
  )
}

export default function Sectors(): JSX.Element {
  const { countryCode } = useParams<{ countryCode: string }>()
  const navigate = useNavigate()
  const code = countryCode ?? ''
  const { data: sectors, isLoading, error } = useSectorRankings(code)
  const { data: countries } = useCountryRankings()

  const country = countries?.find((c) => c.country === code)
  const flag = COUNTRY_FLAGS[code] ?? ''
  const countryName = COUNTRY_NAMES[code] ?? code

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-slate-500 mb-4">
        <Link to="/compass" className="hover:text-teal-600 transition-colors">Countries</Link>
        <span>/</span>
        <span className="text-slate-900 font-medium">{flag} {countryName}</span>
      </nav>

      {/* Country Summary */}
      {country && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-3xl">{flag}</span>
              <div>
                <h1 className="text-xl font-bold text-slate-900">{countryName}</h1>
                <p className="text-sm text-slate-500">{country.name} vs ACWI</p>
              </div>
            </div>
            <div className="flex items-center gap-6">
              <ActionBadge action={country.action} />
              <div className="text-center">
                <div className="text-2xl font-bold font-mono text-slate-900">{country.rs_score?.toFixed(1)}</div>
                <div className="text-xs text-slate-400">RS Score</div>
              </div>
              <div className="flex gap-4 text-center">
                {[
                  { label: '3M', value: country.return_3m },
                  { label: '6M', value: country.return_6m },
                  { label: '12M', value: country.return_12m },
                ].map(({ label, value }) => (
                  <div key={label}>
                    <div className={`text-sm font-mono font-semibold ${
                      (value ?? 0) > 0 ? 'text-emerald-600' : (value ?? 0) < 0 ? 'text-red-600' : 'text-slate-500'
                    }`}>
                      {value != null ? formatPercent(value) : '--'}
                    </div>
                    <div className="text-xs text-slate-400">{label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-slate-800">Sectors in {countryName}</h2>
        <p className="text-sm text-slate-500">Relative strength of sectors vs {countryName} benchmark</p>
      </div>

      {/* Loading / Error */}
      {isLoading && (
        <div className="flex items-center justify-center h-48 text-slate-400">Loading sector data...</div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
          Failed to load sector rankings.
        </div>
      )}

      {/* Table */}
      {sectors && sectors.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Sector</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Action</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">RS Score</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Trend</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Volume</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">1M</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">3M</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">6M</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">12M</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Excess 3M</th>
                <th className="px-3 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Excess 6M</th>
              </tr>
            </thead>
            <tbody>
              {sectors.map((item) => (
                <SectorRow
                  key={item.instrument_id}
                  item={item}
                  onClick={() => navigate(`/compass/country/${code}/sector/${item.sector ?? item.instrument_id}`)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {sectors && sectors.length === 0 && !isLoading && (
        <div className="text-center py-16 text-slate-400">No sector data available for {countryName}.</div>
      )}
    </div>
  )
}
