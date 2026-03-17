import { useParams } from 'react-router-dom'

export default function StockSelection(): JSX.Element {
  const { countryCode, sectorSlug } = useParams<{
    countryCode: string
    sectorSlug: string
  }>()

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">
        Stock Selection — {countryCode} / {sectorSlug}
      </h1>
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-400">
        Stock ranking table and RS charts coming soon.
      </div>
    </div>
  )
}
