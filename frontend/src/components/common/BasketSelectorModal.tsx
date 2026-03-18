import { useState } from 'react'
import { useBaskets } from '@/api/hooks/useBaskets'
import type { Basket } from '@/types/baskets'

interface BasketSelectorModalProps {
  isOpen: boolean
  instrumentId: string
  instrumentName: string
  onClose: () => void
  onSelect: (basketId: string, weight: number) => void
  isAdding?: boolean
}

export default function BasketSelectorModal({
  isOpen,
  instrumentId,
  instrumentName,
  onClose,
  onSelect,
  isAdding = false,
}: BasketSelectorModalProps): JSX.Element | null {
  const { data: basketsData } = useBaskets()
  const baskets: Basket[] = Array.isArray(basketsData) ? basketsData : []
  const activeBaskets = baskets.filter((b: Basket) => b.status === 'active')

  const [selectedBasketId, setSelectedBasketId] = useState('')
  const [weight, setWeight] = useState('10')

  if (!isOpen) return null

  function handleSubmit(e: React.FormEvent): void {
    e.preventDefault()
    if (!selectedBasketId) return
    const w = parseFloat(weight)
    if (Number.isNaN(w) || w <= 0 || w > 100) return
    onSelect(selectedBasketId, w / 100)
    setSelectedBasketId('')
    setWeight('10')
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900">Add to Basket</h2>
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

        <div className="mb-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
          Adding <span className="font-mono font-semibold text-teal-700">{instrumentId}</span>
          {instrumentName && <span className="text-slate-500"> — {instrumentName}</span>}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Select Basket
            </label>
            {activeBaskets.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">
                No active baskets. Create one first from the Baskets page.
              </p>
            ) : (
              <div className="mt-2 max-h-48 space-y-1 overflow-y-auto">
                {activeBaskets.map((basket: Basket) => (
                  <button
                    key={basket.id}
                    type="button"
                    onClick={() => setSelectedBasketId(basket.id)}
                    className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                      selectedBasketId === basket.id
                        ? 'border-teal-500 bg-teal-50 text-teal-800'
                        : 'border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    <span className="font-medium">{basket.name}</span>
                    {basket.description && (
                      <span className="ml-2 text-xs text-slate-400">
                        {basket.description}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700">
              Weight (%)
            </label>
            <input
              type="number"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
              min="0.1"
              max="100"
              step="0.1"
              className="mt-1 w-32 rounded-lg border border-slate-200 px-3 py-2 font-mono text-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
            />
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
              disabled={!selectedBasketId || activeBaskets.length === 0 || isAdding}
              className="flex-1 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50"
            >
              {isAdding ? 'Adding...' : 'Add to Basket'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
