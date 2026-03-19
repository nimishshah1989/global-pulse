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
import type { RankingItem, PriceTrend, VolumeCharacter } from '@/types/rs'
import ActionBadge from '@/components/common/QuadrantBadge'
import { COUNTRY_FLAGS, COUNTRY_NAMES } from '@/data/mockCountryData'

interface RSRankingTableProps {
  data: RankingItem[]
  onRowClick?: (item: RankingItem) => void
  showCountry?: boolean
  showSector?: boolean
  loading?: boolean
}

const columnHelper = createColumnHelper<RankingItem>()

function formatPct(value: number | null): string {
  if (value === null) return '--'
  const prefix = value > 0 ? '+' : ''
  return `${prefix}${value.toFixed(1)}`
}

function TrendArrow({ trend }: { trend: PriceTrend | null }): JSX.Element {
  if (trend === 'OUTPERFORMING') {
    return (
      <span className="inline-flex items-center gap-1">
        <svg className="h-4 w-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
        </svg>
        <span className="text-xs text-emerald-600 font-medium">Out</span>
      </span>
    )
  }
  if (trend === 'UNDERPERFORMING') {
    return (
      <span className="inline-flex items-center gap-1">
        <svg className="h-4 w-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
        <span className="text-xs text-red-600 font-medium">Under</span>
      </span>
    )
  }
  if (trend === 'RECOVERING') {
    return (
      <span className="inline-flex items-center gap-1">
        <svg className="h-4 w-4 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
        </svg>
        <span className="text-xs text-amber-600 font-medium">Recov</span>
      </span>
    )
  }
  if (trend === 'CONSOLIDATING') {
    return (
      <span className="inline-flex items-center gap-1">
        <svg className="h-4 w-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
        <span className="text-xs text-blue-600 font-medium">Consol</span>
      </span>
    )
  }
  return <span className="text-xs text-slate-400">--</span>
}


function VolumeLabel({ character }: { character: VolumeCharacter | null }): JSX.Element {
  if (character === 'ACCUMULATION') {
    return <span className="text-xs font-semibold text-emerald-600">ACCUM</span>
  }
  if (character === 'DISTRIBUTION') {
    return <span className="text-xs font-semibold text-red-600">DIST</span>
  }
  if (character === 'NEUTRAL') {
    return <span className="text-xs text-slate-400">Neutral</span>
  }
  return <span className="text-xs text-slate-400">--</span>
}

export default function RSRankingTable({
  data,
  onRowClick,
  showCountry = false,
  showSector = false,
  loading = false,
}: RSRankingTableProps): JSX.Element {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'rs_score', desc: true },
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
      columnHelper.accessor('action', {
        header: 'Action',
        cell: (info) => <ActionBadge action={info.getValue()} />,
        sortingFn: 'alphanumeric',
      }),
      columnHelper.accessor('return_1m', {
        header: '1M',
        cell: (info) => {
          const val = info.getValue()
          if (val == null) return <span className="text-slate-300">--</span>
          const color = val > 0 ? 'text-emerald-600' : val < 0 ? 'text-red-600' : 'text-slate-500'
          return <span className={`font-mono text-xs font-semibold ${color}`}>{formatPct(val)}%</span>
        },
        sortingFn: 'basic',
      }),
      columnHelper.accessor('return_3m', {
        header: '3M',
        cell: (info) => {
          const val = info.getValue()
          if (val == null) return <span className="text-slate-300">--</span>
          const color = val > 0 ? 'text-emerald-600' : val < 0 ? 'text-red-600' : 'text-slate-500'
          return <span className={`font-mono text-xs font-semibold ${color}`}>{formatPct(val)}%</span>
        },
        sortingFn: 'basic',
      }),
      columnHelper.accessor('return_6m', {
        header: '6M',
        cell: (info) => {
          const val = info.getValue()
          if (val == null) return <span className="text-slate-300">--</span>
          const color = val > 0 ? 'text-emerald-600' : val < 0 ? 'text-red-600' : 'text-slate-500'
          return <span className={`font-mono text-xs font-semibold ${color}`}>{formatPct(val)}%</span>
        },
        sortingFn: 'basic',
      }),
      columnHelper.accessor('return_12m', {
        header: '12M',
        cell: (info) => {
          const val = info.getValue()
          if (val == null) return <span className="text-slate-300">--</span>
          const color = val > 0 ? 'text-emerald-600' : val < 0 ? 'text-red-600' : 'text-slate-500'
          return <span className={`font-mono text-xs font-semibold ${color}`}>{formatPct(val)}%</span>
        },
        sortingFn: 'basic',
      }),
      columnHelper.accessor('price_trend', {
        header: 'Trend',
        cell: (info) => <TrendArrow trend={info.getValue()} />,
        sortingFn: 'alphanumeric',
      }),
      columnHelper.accessor('volume_character', {
        header: 'Volume',
        cell: (info) => <VolumeLabel character={info.getValue()} />,
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
