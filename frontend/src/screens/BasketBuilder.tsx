import { useParams } from 'react-router-dom'

export default function BasketBuilder(): JSX.Element {
  const { basketId } = useParams<{ basketId: string }>()

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">
        {basketId ? `Basket — ${basketId}` : 'My Baskets'}
      </h1>
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-400">
        Basket builder and simulator coming soon.
      </div>
    </div>
  )
}
