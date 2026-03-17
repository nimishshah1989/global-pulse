interface Props {
  rows?: number
  type?: 'table' | 'chart' | 'card'
}

function SkeletonPulse({ className }: { className: string }): JSX.Element {
  return <div className={`animate-pulse rounded bg-slate-200 ${className}`} />
}

function TableSkeleton({ rows }: { rows: number }): JSX.Element {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      {/* Header */}
      <div className="flex gap-4 border-b border-slate-200 bg-slate-50 px-4 py-3">
        {Array.from({ length: 6 }, (_, i) => (
          <SkeletonPulse key={i} className="h-3 w-20" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }, (_, rowIdx) => (
        <div
          key={rowIdx}
          className="flex items-center gap-4 border-b border-slate-100 px-4 py-3 last:border-b-0"
        >
          <SkeletonPulse className="h-3 w-24" />
          <SkeletonPulse className="h-3 w-32" />
          <SkeletonPulse className="h-3 w-14" />
          <SkeletonPulse className="h-3 w-16" />
          <SkeletonPulse className="h-3 w-14" />
          <SkeletonPulse className="h-3 w-20" />
        </div>
      ))}
    </div>
  )
}

function ChartSkeleton(): JSX.Element {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6">
      <SkeletonPulse className="mb-4 h-4 w-48" />
      <SkeletonPulse className="h-64 w-full" />
    </div>
  )
}

function CardSkeleton({ rows }: { rows: number }): JSX.Element {
  return (
    <div className="grid gap-4">
      {Array.from({ length: rows }, (_, i) => (
        <div
          key={i}
          className="rounded-xl border border-slate-200 bg-white p-5"
        >
          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <SkeletonPulse className="h-4 w-40" />
              <SkeletonPulse className="h-3 w-64" />
            </div>
            <SkeletonPulse className="h-5 w-16 rounded-full" />
          </div>
          <div className="mt-3 flex gap-6">
            <SkeletonPulse className="h-3 w-28" />
            <SkeletonPulse className="h-3 w-24" />
          </div>
        </div>
      ))}
    </div>
  )
}

export default function LoadingSkeleton({
  rows = 6,
  type = 'table',
}: Props): JSX.Element {
  switch (type) {
    case 'chart':
      return <ChartSkeleton />
    case 'card':
      return <CardSkeleton rows={rows} />
    case 'table':
    default:
      return <TableSkeleton rows={rows} />
  }
}
