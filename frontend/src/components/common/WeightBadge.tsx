import type { Quadrant } from '@/types/rs'

type WeightCall = 'OVERWEIGHT' | 'NEUTRAL' | 'UNDERWEIGHT'

interface WeightInfo {
  call: WeightCall
  label: string
  color: string
  bgColor: string
  borderColor: string
  description: string
}

/**
 * Determine overweight/underweight/neutral call based on RS score,
 * momentum, and quadrant. This gives traders a clear actionable view.
 */
export function getWeightRecommendation(
  rsScore: number,
  rsMomentum: number,
  quadrant: Quadrant,
): WeightInfo {
  // LEADING with strong score = Overweight
  if (quadrant === 'LEADING' && rsScore >= 55) {
    return {
      call: 'OVERWEIGHT',
      label: 'Overweight',
      color: 'text-emerald-700',
      bgColor: 'bg-emerald-50',
      borderColor: 'border-emerald-200',
      description: 'Strong RS + rising momentum — allocate above benchmark weight',
    }
  }

  // IMPROVING with positive momentum = early Overweight signal
  if (quadrant === 'IMPROVING' && rsMomentum > 3) {
    return {
      call: 'OVERWEIGHT',
      label: 'Overweight',
      color: 'text-emerald-700',
      bgColor: 'bg-emerald-50',
      borderColor: 'border-emerald-200',
      description: 'Momentum turning positive — early overweight signal',
    }
  }

  // WEAKENING = start reducing
  if (quadrant === 'WEAKENING') {
    return {
      call: 'NEUTRAL',
      label: 'Neutral',
      color: 'text-amber-700',
      bgColor: 'bg-amber-50',
      borderColor: 'border-amber-200',
      description: 'RS still strong but momentum fading — reduce to neutral',
    }
  }

  // LAGGING = underweight
  if (quadrant === 'LAGGING') {
    return {
      call: 'UNDERWEIGHT',
      label: 'Underweight',
      color: 'text-red-700',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      description: 'Weak RS + falling momentum — allocate below benchmark weight',
    }
  }

  // Default neutral
  return {
    call: 'NEUTRAL',
    label: 'Neutral',
    color: 'text-amber-700',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    description: 'No clear directional signal — hold at benchmark weight',
  }
}

interface WeightBadgeProps {
  rsScore: number
  rsMomentum: number
  quadrant: Quadrant
  showDescription?: boolean
}

export default function WeightBadge({
  rsScore,
  rsMomentum,
  quadrant,
  showDescription = false,
}: WeightBadgeProps): JSX.Element {
  const info = getWeightRecommendation(rsScore, rsMomentum, quadrant)

  return (
    <div className="inline-flex flex-col">
      <span
        className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-bold ${info.bgColor} ${info.borderColor} ${info.color}`}
      >
        {info.call === 'OVERWEIGHT' && '▲ '}
        {info.call === 'UNDERWEIGHT' && '▼ '}
        {info.label}
      </span>
      {showDescription && (
        <span className="mt-0.5 text-[10px] text-slate-500">
          {info.description}
        </span>
      )}
    </div>
  )
}
