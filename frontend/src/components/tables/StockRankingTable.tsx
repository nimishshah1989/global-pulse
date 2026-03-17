import { useMemo, useState } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from '@tanstack/react-table'
import type { RankingItem } from '@/types/rs'
import QuadrantBadge from '@/components/common/QuadrantBadge'
import LiquidityBadge from '@/components/common/LiquidityBadge'
import ExtensionBadge from '@/components/common/ExtensionBadge'

interface StockRankingTableProps {
  data: RankingItem[]
  onAddToBasket?: (item: RankingItem) => void
  onRowClick?: (item: RankingItem) => void
}

const columnHelper = createColumnHelper<RankingItem>()

function formatPct(value: number): string {
  const prefix = value > 0 ? '+' : ''
  return `${prefix}${value.toFixed(1)}`
}

export default function StockRankingTable({
  data,
  onAddToBasket,
  onRowClick,
}: StockRankingTableProps): JSX.Element {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'adjusted_rs_score', desc: true },
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
      columnHelper.accessor('adjusted_rs_score', {
        header: 'RS Score',
        cell: (info) => (
          <span className="font-mono font-semibold text-slate-900">
            {info.getValue().toFixed(1)}
          </span>
        ),
        sortingFn: 'basic',
      }),
      columnHelper.accessor('quadrant', {
        header: 'Quadrant',
        cell: (info) => <QuadrantBadge quadrant={info.getValue()} />,
        sortingFn: 'alphanumeric',
      }),
      columnHelper.accessor('rs_momentum', {
        header: 'Momentum',
        cell: (info) => {
          const val = info.getValue()
          const color = val > 0 ? 'text-emerald-600' : val < 0 ? 'text-red-600' : 'text-slate-500'
          return <span className={`font-mono font-medium ${color}`}>{formatPct(val)}</span>
        },
        sortingFn: 'basic',
      }),
      columnHelper.accessor('volume_ratio', {
        header: 'Vol Ratio',
        cell: (info) => {
          const val = info.getValue()
          const color = val >= 1.0 ? 'text-emerald-600' : 'text-red-600'
          return <span className={`font-mono font-medium ${color}`}>{val.toFixed(2)}</span>
        },
        sortingFn: 'basic',
      }),
      columnHelper.accessor('liquidity_tier', {
        header: 'Liquidity',
        cell: (info) => <LiquidityBadge tier={info.getValue() as 1 | 2 | 3} />,
        sortingFn: 'basic',
      }),
      columnHelper.accessor('rs_pct_1m', {
        header: '1M',
        cell: (info) => <span className="font-mono text-slate-700">{info.getValue().toFixed(0)}</span>,
        sortingFn: 'basic',
      }),
      columnHelper.accessor('rs_pct_3m', {
        header: '3M',
        cell: (info) => <span className="font-mono text-slate-700">{info.getValue().toFixed(0)}</span>,
        sortingFn: 'basic',
      }),
      columnHelper.accessor('rs_pct_6m', {
        header: '6M',
        cell: (info) => <span className="font-mono text-slate-700">{info.getValue().toFixed(0)}</span>,
        sortingFn: 'basic',
      }),
      columnHelper.accessor('rs_pct_12m', {
        header: '12M',
        cell: (info) => <span className="font-mono text-slate-700">{info.getValue().toFixed(0)}</span>,
        sortingFn: 'basic',
      }),
      columnHelper.display({
        id: 'actions',
        header: '',
        cell: (info) => (
          <div className="flex items-center gap-2">
            {info.row.original.extension_warning && <ExtensionBadge />}
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
