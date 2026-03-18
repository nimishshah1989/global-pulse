import type { Action } from '@/types/rs'

interface WeightBadgeProps {
  action: Action
  showDescription?: boolean
}

interface WeightInfo {
  label: string
  color: string
  bgColor: string
  borderColor: string
  description: string
}

const WEIGHT_MAP: Record<Action, WeightInfo> = {
  BUY: { label: 'Overweight', color: 'text-emerald-700', bgColor: 'bg-emerald-50', borderColor: 'border-emerald-200', description: 'Outperforming + accelerating + accumulation' },
  HOLD_DIVERGENCE: { label: 'Neutral', color: 'text-yellow-700', bgColor: 'bg-yellow-50', borderColor: 'border-yellow-200', description: 'Outperforming + accelerating but distribution' },
  HOLD_FADING: { label: 'Neutral', color: 'text-yellow-700', bgColor: 'bg-yellow-50', borderColor: 'border-yellow-200', description: 'Outperforming but momentum fading' },
  REDUCE: { label: 'Reduce', color: 'text-orange-700', bgColor: 'bg-orange-50', borderColor: 'border-orange-200', description: 'Outperforming but fading with distribution' },
  SELL: { label: 'Underweight', color: 'text-red-700', bgColor: 'bg-red-50', borderColor: 'border-red-200', description: 'Underperforming + decelerating + distribution' },
  WATCH: { label: 'Watch', color: 'text-blue-700', bgColor: 'bg-blue-50', borderColor: 'border-blue-200', description: 'Underperforming but accumulation starting' },
  ACCUMULATE: { label: 'Accumulate', color: 'text-teal-700', bgColor: 'bg-teal-50', borderColor: 'border-teal-200', description: 'Momentum turning + accumulation detected' },
  AVOID: { label: 'Avoid', color: 'text-slate-600', bgColor: 'bg-slate-50', borderColor: 'border-slate-200', description: 'Momentum turning but on distribution' },
}

export default function WeightBadge({ action, showDescription = false }: WeightBadgeProps): JSX.Element {
  const info = WEIGHT_MAP[action] ?? WEIGHT_MAP.WATCH
  return (
    <div className="inline-flex flex-col">
      <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-bold ${info.bgColor} ${info.borderColor} ${info.color}`}>
        {info.label}
      </span>
      {showDescription && (
        <span className="mt-0.5 text-[10px] text-slate-500">{info.description}</span>
      )}
    </div>
  )
}
