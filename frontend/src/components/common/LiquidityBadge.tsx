interface LiquidityBadgeProps {
  tier: 1 | 2 | 3
}

const TIER_STYLES: Record<number, { bg: string; text: string; label: string }> = {
  1: {
    bg: 'bg-emerald-100',
    text: 'text-emerald-700',
    label: 'High',
  },
  2: {
    bg: 'bg-amber-100',
    text: 'text-amber-700',
    label: 'Medium',
  },
  3: {
    bg: 'bg-red-100',
    text: 'text-red-700',
    label: 'Low',
  },
}

export default function LiquidityBadge({ tier }: LiquidityBadgeProps): JSX.Element {
  const style = TIER_STYLES[tier]

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${style.bg} ${style.text}`}
    >
      {style.label}
    </span>
  )
}
