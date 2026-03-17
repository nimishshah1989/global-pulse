import { useMemo } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from '@tanstack/react-table'
import { useState } from 'react'
import type { RankingItem } from '@/types/rs'
import QuadrantBadge from '@/components/common/QuadrantBadge'
import { COUNTRY_FLAGS, COUNTRY_NAMES } from '@/data/mockCountryData'

interface RSRankingTableProps {
  data: RankingItem[]
  onRowClick?: (item: RankingItem) => void
  showCountry?: boolean
  showSector?: boolean
  loading?: boolean
}

const columnHelper = createColumnHelper<RankingItem>()

function formatPct(value: number): string {
  const prefix = value > 0 ? '+' : ''
  return `${prefix}${value.toFixed(1)}`
}

function TrendArrow({ trend }: { trend: string }): JSX.Element {
  if (trend === 'OUTPERFORMING') {
    return (
      <svg className="h-4 w-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
      </svg>
    )
  }
  return (
    <svg className="h-4 w-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  )
}

export default function RSRankingTable({
  data,
  onRowClick,
  showCountry = false,
  showSector = false,
  loading = false,
}: RSRankingTableProps): JSX.Element {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'adjusted_rs_score', desc: true },
  ])

  const columns = useMemo(() => {
    const cols = []

    if (showCountry) {
      cols.push(
        columnHelper.accessor('country', {
          header: 'Country',
          cell: (info) => {
            const code = info.getValue()
            const flag = code ? COUNTRY_FLAGS[code] ?? '' : ''
            const name = code ? COUNTRY_NAMES[code] ?? code : ''
            return (
              <span className="flex items-center gap-2 whitespace-nowrap">
                <span>{flag}</span>
                <span className="font-medium text-slate-900">{name}</span>
              </span>
            )
          },
          sortingFn: 'alphanumeric',
        }),
      )
    }

    if (showSector) {
      cols.push(
        columnHelper.accessor('name', {
          header: 'Sector',
          cell: (info) => (
            <span className="font-medium text-slate-900 whitespace-nowrap">
              {info.getValue()}
            </span>
          ),
          sortingFn: 'alphanumeric',
        }),
      )
    }

    cols.push(
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
      columnHelper.accessor('volume_ratio', {
        header: 'Vol Ratio',
        cell: (info) => {
          const val = info.getValue()
          const color = val >= 1.0 ? 'text-emerald-600' : 'text-red-600'
          return <span className={`font-mono font-medium ${color}`}>{val.toFixed(2)}</span>
        },
        sortingFn: 'basic',
      }),
      columnHelper.accessor('rs_trend', {
        header: 'Trend',
        cell: (info) => <TrendArrow trend={info.getValue()} />,
        sortingFn: 'alphanumeric',
      }),
    )

    return cols
  }, [showCountry, showSector])

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center rounded-xl border border-slate-200 bg-white p-12">
        <span className="text-sm text-slate-400">Loading rankings...</span>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
      <table className="w-full text-sm">
        <thead className="sticky top-0 z-10 bg-slate-50 border-b border-slate-200">
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
                    {{
                      asc: ' \u2191',
                      desc: ' \u2193',
                    }[header.column.getIsSorted() as string] ?? ''}
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
