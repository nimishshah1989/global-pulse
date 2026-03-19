import { useMemo, useState } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from '@tanstack/react-table'
import { getTrendColor, getVolumeColor } from '@/utils/trend'
import type { RankingItem } from '@/types/rs'
import { QuadrantBadge } from '@/components/common/QuadrantBadge'

interface StockRankingTableProps {
  data: RankingItem[]
  onAddToBasket?: (item: RankingItem) => void
  onRowClick?: (item: RankingItem) => void
}

const columnHelper = createColumnHelper<RankingItem>()

export default function StockRankingTable({
  data,
  onAddToBasket,
  onRowClick,
}: StockRankingTableProps): JSX.Element {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'rs_score', desc: true },
  ])

  const columns = useMemo(
    () => [
      columnHelper.accessor('instrument_id', {
        header: 'Ticker',
        cell: (info) => {
          const val = info.getValue()
          const ticker = val.replace(/_US$/, '')
          return (
            <span className="font-mono font-semibold text-teal-700">
              {ticker}
            </span>
          )
        },
        sortingFn: 'alphanumeric',
      }),
      columnHelper.accessor('name', {
        header: 'Name',
        cell: (info) => (
          <span className="whitespace-nowrap font-medium text-slate-900">
            {info.getValue()}
          </span>
        ),
        sortingFn: 'alphanumeric',
      }),
      columnHelper.accessor('rs_score', {
        header: 'RS Score',
        cell: (info) => (
          <span className="font-mono font-semibold text-slate-900">
            {info.getValue().toFixed(1)}
          </span>
        ),
        sortingFn: 'basic',
      }),
      columnHelper.accessor('action', {
        header: 'Action',
        cell: (info) => <QuadrantBadge action={info.getValue()} />,
        sortingFn: 'alphanumeric',
      }),
      columnHelper.accessor('rs_momentum_pct', {
        header: 'Momentum',
        cell: (info) => {
          const val = info.getValue()
          if (val === null) return <span className="text-slate-400">-</span>
          const color = val > 0 ? 'text-emerald-600' : val < 0 ? 'text-red-600' : 'text-slate-500'
          const prefix = val > 0 ? '+' : ''
          return <span className={`font-mono font-medium ${color}`}>{prefix}{val.toFixed(1)}%</span>
        },
        sortingFn: 'basic',
      }),
      columnHelper.accessor('volume_character', {
        header: 'Volume',
        cell: (info) => {
          const val = info.getValue()
          if (!val) return <span className="text-slate-400">-</span>
          return <span className={`text-xs font-medium ${getVolumeColor(val)}`}>{val}</span>
        },
        sortingFn: 'alphanumeric',
      }),
      columnHelper.accessor('price_trend', {
        header: 'Trend',
        cell: (info) => {
          const val = info.getValue()
          if (!val) return <span className="text-slate-400">-</span>
          return <span className={`text-xs font-medium ${getTrendColor(val)}`}>{val}</span>
        },
        sortingFn: 'alphanumeric',
      }),
      columnHelper.display({
        id: 'actions',
        header: '',
        cell: (info) => (
          <div className="flex items-center gap-2">
            {onAddToBasket && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onAddToBasket(info.row.original)
                }}
                className="whitespace-nowrap rounded-lg bg-teal-50 px-2.5 py-1 text-xs font-semibold text-teal-700 hover:bg-teal-100"
                data-testid="add-to-basket-btn"
              >
                + Basket
              </button>
            )}
          </div>
        ),
      }),
    ],
    [onAddToBasket],
  )

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white" data-testid="stock-ranking-table">
      <table className="w-full text-sm">
        <thead className="sticky top-0 z-10 border-b border-slate-200 bg-slate-50">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th
                  key={header.id}
                  onClick={header.column.getToggleSortingHandler()}
                  className="cursor-pointer select-none px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500 hover:text-slate-700"
                >
                  <span className="flex items-center gap-1">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {{ asc: ' \u2191', desc: ' \u2193' }[
                      header.column.getIsSorted() as string
                    ] ?? ''}
                  </span>
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody className="divide-y divide-slate-100">
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              onClick={() => onRowClick?.(row.original)}
              className={`transition-colors hover:bg-slate-50 ${onRowClick ? 'cursor-pointer' : ''}`}
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-4 py-3">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
