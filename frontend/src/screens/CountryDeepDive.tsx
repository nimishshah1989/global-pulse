import { useParams } from 'react-router-dom'

export default function CountryDeepDive(): JSX.Element {
  const { countryCode } = useParams<{ countryCode: string }>()

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">
        Country Deep Dive — {countryCode}
      </h1>
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-400">
        RRG scatter plot and sector rankings coming soon.
      </div>
    </div>
  )
}
