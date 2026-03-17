import { useState } from 'react'

interface CreateBasketModalProps {
  isOpen: boolean
  onClose: () => void
  onCreate: (data: {
    name: string
    description: string
    benchmark_id: string
    weighting_method: 'equal' | 'manual' | 'rs_weighted'
  }) => void
}

export default function CreateBasketModal({
  isOpen,
  onClose,
  onCreate,
}: CreateBasketModalProps): JSX.Element | null {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [benchmarkId, setBenchmarkId] = useState('ACWI')
  const [weightingMethod, setWeightingMethod] = useState<'equal' | 'manual' | 'rs_weighted'>('equal')

  if (!isOpen) return null

  function handleSubmit(e: React.FormEvent): void {
    e.preventDefault()
    if (!name.trim()) return
    onCreate({
      name: name.trim(),
      description: description.trim(),
      benchmark_id: benchmarkId,
      weighting_method: weightingMethod,
    })
    setName('')
    setDescription('')
    setBenchmarkId('ACWI')
    setWeightingMethod('equal')
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900">Create New Basket</h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600"
            aria-label="Close"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Asia Momentum Leaders"
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What thesis does this basket represent?"
              rows={2}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700">Benchmark</label>
            <select
              value={benchmarkId}
              onChange={(e) => setBenchmarkId(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
            >
              <option value="ACWI">MSCI ACWI</option>
              <option value="SPX">S&P 500</option>
              <option value="NSEI">NIFTY 50</option>
              <option value="NKX">Nikkei 225</option>
              <option value="DAX">DAX 40</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700">Weighting Method</label>
            <select
              value={weightingMethod}
              onChange={(e) => setWeightingMethod(e.target.value as 'equal' | 'manual' | 'rs_weighted')}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
            >
              <option value="equal">Equal Weight</option>
              <option value="manual">Manual Weight</option>
              <option value="rs_weighted">RS-Weighted</option>
            </select>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700"
            >
              Create Basket
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
