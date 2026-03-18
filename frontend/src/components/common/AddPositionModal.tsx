import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import apiClient from '@/api/client'

interface Instrument {
  id: string
  name: string
  asset_type: string
  country: string | null
  sector: string | null
}

interface AddPositionModalProps {
  isOpen: boolean
  onClose: () => void
  onAdd: (instrumentId: string, weight: number) => void
  isAdding?: boolean
}

export default function AddPositionModal({
  isOpen,
  onClose,
  onAdd,
  isAdding = false,
}: AddPositionModalProps): JSX.Element | null {
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState('')
  const [weight, setWeight] = useState('10')

  const { data: instruments } = useQuery<Instrument[]>({
    queryKey: ['instruments-search'],
    queryFn: async () => {
      const response = await apiClient.get<Instrument[]>('/instruments')
      return response.data
    },
    enabled: isOpen,
    staleTime: 60_000,
  })

  const filtered = useMemo(() => {
    if (!instruments || !search.trim()) return []
    const q = search.toLowerCase()
    return instruments
      .filter(
        (i) =>
          i.id.toLowerCase().includes(q) ||
          i.name.toLowerCase().includes(q) ||
          (i.sector && i.sector.toLowerCase().includes(q)),
      )
      .slice(0, 20)
  }, [instruments, search])

  if (!isOpen) return null

  function handleSubmit(e: React.FormEvent): void {
    e.preventDefault()
    if (!selectedId) return
    const w = parseFloat(weight)
    if (Number.isNaN(w) || w <= 0 || w > 100) return
    onAdd(selectedId, w / 100)
    setSearch('')
    setSelectedId('')
    setWeight('10')
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-xl border border-slate-200 bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900">Add Position</h2>
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
            <label className="block text-sm font-medium text-slate-700">
              Search Instrument
            </label>
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setSelectedId('')
              }}
              placeholder="e.g. AAPL, Technology, XLK..."
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
            />
          </div>

          {filtered.length > 0 && !selectedId && (
            <div className="max-h-48 overflow-y-auto rounded-lg border border-slate-200">
              {filtered.map((inst) => (
                <button
                  key={inst.id}
                  type="button"
                  onClick={() => {
                    setSelectedId(inst.id)
                    setSearch(`${inst.id} — ${inst.name}`)
                  }}
                  className="flex w-full items-center gap-3 px-3 py-2 text-left text-sm hover:bg-teal-50"
                >
                  <span className="font-mono font-semibold text-teal-700">
                    {inst.id}
                  </span>
                  <span className="text-slate-600">{inst.name}</span>
                  {inst.country && (
                    <span className="ml-auto text-xs text-slate-400">
                      {inst.country}
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}

          {selectedId && (
            <div className="rounded-lg border border-teal-200 bg-teal-50 px-3 py-2 text-sm text-teal-800">
              Selected: <span className="font-mono font-semibold">{selectedId}</span>
            </div>
          )}

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
              disabled={!selectedId || isAdding}
              className="flex-1 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50"
            >
              {isAdding ? 'Adding...' : 'Add Position'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
