import type { Quadrant } from '@/types/rs'

interface QuadrantBadgeProps {
  quadrant: Quadrant
}

const QUADRANT_STYLES: Record<Quadrant, { bg: string; text: string; label: string }> = {
  LEADING: {
    bg: 'bg-emerald-100',
    text: 'text-emerald-700',
    label: 'Leading',
  },
  WEAKENING: {
    bg: 'bg-amber-100',
    text: 'text-amber-700',
    label: 'Weakening',
  },
  LAGGING: {
    bg: 'bg-red-100',
    text: 'text-red-700',
    label: 'Lagging',
  },
  IMPROVING: {
    bg: 'bg-blue-100',
    text: 'text-blue-700',
    label: 'Improving',
  },
}

export default function QuadrantBadge({ quadrant }: QuadrantBadgeProps): JSX.Element {
  const style = QUADRANT_STYLES[quadrant]

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${style.bg} ${style.text}`}
    >
      {style.label}
    </span>
  )
}
