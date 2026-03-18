import type { Opportunity } from '@/types/opportunities'

interface AlignmentCardProps {
  opportunity: Opportunity
  onClick?: () => void
}

interface AlignmentMeta {
  country: string
  country_quadrant: string
  sector: string
  sector_quadrant: string
  stock: string
  stock_quadrant: string
}

function isAlignmentMeta(meta: Record<string, unknown>): meta is Record<string, unknown> & AlignmentMeta {
  return (
    typeof meta.country === 'string' &&
    typeof meta.sector === 'string' &&
    typeof meta.stock === 'string'
  )
}

export default function AlignmentCard({ opportunity, onClick }: AlignmentCardProps): JSX.Element {
  const meta = opportunity.metadata
  const hasChain = meta != null && typeof meta === 'object' && isAlignmentMeta(meta)

  return (
    <div
      onClick={onClick}
      className={`rounded-xl border-2 border-teal-200 bg-teal-50/50 p-5 transition-shadow hover:shadow-md ${onClick ? 'cursor-pointer' : ''}`}
      data-testid="alignment-card"
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-teal-700">
          Multi-Level Alignment
        </span>
        <span className="rounded-full bg-teal-600 px-3 py-0.5 font-mono text-xs font-bold text-white">
          {opportunity.conviction_score}
        </span>
      </div>

      {hasChain ? (
        <div className="space-y-2" data-testid="alignment-chain">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-base">🌍</span>
            <span className="font-medium text-slate-900">
              {meta.country as string}
            </span>
            <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-xs font-semibold text-emerald-700">
              {meta.country_quadrant as string}
            </span>
          </div>

          <div className="ml-4 flex items-center gap-2 text-sm">
            <span className="text-slate-300">&#8594;</span>
            <span className="text-base">📊</span>
            <span className="font-medium text-slate-900">
              {meta.sector as string}
            </span>
            <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-xs font-semibold text-emerald-700">
              {meta.sector_quadrant as string}
            </span>
          </div>

          <div className="ml-8 flex items-center gap-2 text-sm">
            <span className="text-slate-300">&#8594;</span>
            <span className="text-base">🔍</span>
            <span className="font-medium text-slate-900">
              {meta.stock as string}
            </span>
            <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-xs font-semibold text-emerald-700">
              {meta.stock_quadrant as string}
            </span>
          </div>
        </div>
      ) : (
        <p className="text-sm text-slate-700">{opportunity.description}</p>
      )}

      <div className="mt-3 text-xs text-slate-500">
        {opportunity.instrument_name} &middot; {opportunity.date}
      </div>
    </div>
  )
}
