import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { formatPercent, formatDate } from '@/utils/format'
import QuadrantBadge from '@/components/common/QuadrantBadge'
import PerformanceStats from '@/components/common/PerformanceStats'
import CreateBasketModal from '@/components/common/CreateBasketModal'
import AddPositionModal from '@/components/common/AddPositionModal'
import BasketNAVChart from '@/components/charts/BasketNAVChart'
import LoadingSkeleton from '@/components/common/LoadingSkeleton'
import ErrorAlert from '@/components/common/ErrorAlert'
import { useBaskets, useBasket, useCreateBasket, useAddPosition, useRemovePosition } from '@/api/hooks/useBaskets'
import {
  MOCK_BASKETS,
  MOCK_POSITION_DETAILS,
  MOCK_BASKET_PERFORMANCE,
  generateMockNAVHistory,
} from '@/data/mockBasketData'
import type { Basket } from '@/types/baskets'

function BasketListView(): JSX.Element {
  const navigate = useNavigate()
  const [showModal, setShowModal] = useState(false)

  const { data: basketsData, isLoading, error, refetch } = useBaskets()
  const createBasketMutation = useCreateBasket()

  const baskets = basketsData ?? MOCK_BASKETS

  function handleCreate(data: {
    name: string
    description: string
    benchmark_id: string
    weighting_method: 'equal' | 'manual' | 'rs_weighted'
  }): void {
    createBasketMutation.mutate(data, {
      onSuccess: () => {
        setShowModal(false)
      },
    })
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">📦 My Baskets</h1>
          <p className="text-sm text-slate-500">
            Create, simulate, and track investment theses
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700"
        >
          + Create New Basket
        </button>
      </div>

      {error && (
        <ErrorAlert
          message={error instanceof Error ? error.message : 'Unknown error'}
          onRetry={() => void refetch()}
        />
      )}

      {isLoading ? (
        <LoadingSkeleton type="card" rows={3} />
      ) : (
        <div className="grid gap-4">
          {baskets.map((basket: Basket) => (
            <div
              key={basket.id}
              onClick={() => navigate(`/compass/baskets/${basket.id}`)}
              className="cursor-pointer rounded-xl border border-slate-200 bg-white p-5 transition-shadow hover:shadow-md"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-slate-900">{basket.name}</h3>
                  {basket.description && (
                    <p className="mt-1 text-sm text-slate-500">{basket.description}</p>
                  )}
                </div>
                <span className="rounded-full bg-teal-50 px-3 py-0.5 text-xs font-semibold text-teal-700">
                  {basket.status}
                </span>
              </div>
              <div className="mt-3 flex items-center gap-6 text-sm text-slate-600">
                <span>Created {formatDate(basket.created_at)}</span>
                <span className="font-mono">
                  Weighting: {basket.weighting_method}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      <CreateBasketModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onCreate={handleCreate}
      />
    </div>
  )
}

function BasketDetailView({ basketId }: { basketId: string }): JSX.Element {
  const navigate = useNavigate()
  const { data: basketData, isLoading, error, refetch } = useBasket(basketId)
  const addPositionMutation = useAddPosition()
  const removePositionMutation = useRemovePosition()
  const [showAddPosition, setShowAddPosition] = useState(false)
  const [showCompare, setShowCompare] = useState(false)

  const { data: allBasketsData } = useBaskets()
  const allBaskets = allBasketsData ?? MOCK_BASKETS
  const otherBaskets = allBaskets.filter((b: Basket) => b.id !== basketId && b.status === 'active')

  const basket = basketData ?? MOCK_BASKETS.find((b) => b.id === basketId) ?? MOCK_BASKETS[0]
  const navHistory = useMemo(() => generateMockNAVHistory(), [])

  function handleAddPosition(instrumentId: string, weight: number): void {
    addPositionMutation.mutate(
      { basketId, instrument_id: instrumentId, weight },
      { onSuccess: () => setShowAddPosition(false) },
    )
  }

  function handleRemovePosition(positionId: string): void {
    removePositionMutation.mutate({ basketId, positionId })
  }

  if (isLoading) {
    return (
      <div className="space-y-5">
        <LoadingSkeleton type="chart" />
        <LoadingSkeleton type="table" rows={4} />
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {error && (
        <ErrorAlert
          message={error instanceof Error ? error.message : 'Unknown error'}
          onRetry={() => void refetch()}
        />
      )}

      <div>
        <nav className="flex items-center gap-2 text-sm text-slate-500">
          <a href="/compass/baskets" className="hover:text-teal-600">Baskets</a>
          <span className="text-slate-300">/</span>
          <span className="font-medium text-slate-900">{basket.name}</span>
        </nav>
        <h1 className="mt-2 text-2xl font-bold text-slate-900">{basket.name}</h1>
        {basket.description && (
          <p className="text-sm text-slate-500">{basket.description}</p>
        )}
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <BasketNAVChart data={navHistory} />
        </div>
        <div>
          <PerformanceStats performance={MOCK_BASKET_PERFORMANCE} />
        </div>
      </div>

      <div>
        <h2 className="mb-3 text-lg font-semibold text-slate-900">Positions</h2>
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Instrument
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Weight
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Return
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                  RS Score
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Quadrant
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {MOCK_POSITION_DETAILS.map((pos) => (
                <tr key={pos.instrument_id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <div>
                      <span className="font-mono font-semibold text-teal-700">
                        {pos.instrument_id.replace(/_US$/, '')}
                      </span>
                      <span className="ml-2 text-slate-500">{pos.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-700">
                    {(pos.weight * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`font-mono font-medium ${pos.position_return >= 0 ? 'text-emerald-600' : 'text-red-600'}`}
                    >
                      {formatPercent(pos.position_return)}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono font-semibold text-slate-900">
                    {pos.adjusted_rs_score.toFixed(1)}
                  </td>
                  <td className="px-4 py-3">
                    <QuadrantBadge quadrant={pos.quadrant} />
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleRemovePosition(pos.instrument_id)}
                      className="text-xs font-medium text-red-500 hover:text-red-700"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex gap-3">
        <button
          onClick={() => setShowAddPosition(true)}
          className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700"
        >
          + Add Position
        </button>
        <button
          onClick={() => setShowCompare(!showCompare)}
          className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Compare with...
        </button>
      </div>

      {showCompare && (
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">
            Select a basket to compare
          </h3>
          {otherBaskets.length === 0 ? (
            <p className="text-sm text-slate-500">No other active baskets to compare with.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {otherBaskets.map((b: Basket) => (
                <button
                  key={b.id}
                  onClick={() => {
                    setShowCompare(false)
                    navigate(`/compass/baskets/${b.id}`)
                  }}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-teal-500 hover:bg-teal-50 hover:text-teal-800"
                >
                  {b.name}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      <AddPositionModal
        isOpen={showAddPosition}
        onClose={() => setShowAddPosition(false)}
        onAdd={handleAddPosition}
        isAdding={addPositionMutation.isPending}
      />
    </div>
  )
}

export default function BasketBuilder(): JSX.Element {
  const { basketId } = useParams<{ basketId: string }>()

  if (basketId) {
    return <BasketDetailView basketId={basketId} />
  }

  return <BasketListView />
}
