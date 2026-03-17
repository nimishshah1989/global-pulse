import type { SignalType } from '@/types/opportunities'

interface SignalTypeBadgeProps {
  signalType: SignalType
}

const SIGNAL_STYLES: Record<SignalType, { bg: string; text: string; label: string }> = {
  quadrant_entry_leading: {
    bg: 'bg-emerald-100',
    text: 'text-emerald-700',
    label: 'Entry: Leading',
  },
  quadrant_entry_improving: {
    bg: 'bg-blue-100',
    text: 'text-blue-700',
    label: 'Entry: Improving',
  },
  volume_breakout: {
    bg: 'bg-purple-100',
    text: 'text-purple-700',
    label: 'Volume Breakout',
  },
  multi_level_alignment: {
    bg: 'bg-teal-100',
    text: 'text-teal-700',
    label: 'Multi-Level',
  },
  bearish_divergence: {
    bg: 'bg-red-100',
    text: 'text-red-700',
    label: 'Bearish Div.',
  },
  bullish_divergence: {
    bg: 'bg-emerald-100',
    text: 'text-emerald-700',
    label: 'Bullish Div.',
  },
  regime_change: {
    bg: 'bg-amber-100',
    text: 'text-amber-700',
    label: 'Regime Change',
  },
  extension_alert: {
    bg: 'bg-orange-100',
    text: 'text-orange-700',
    label: 'Extension',
  },
}

export default function SignalTypeBadge({ signalType }: SignalTypeBadgeProps): JSX.Element {
  const style = SIGNAL_STYLES[signalType]

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${style.bg} ${style.text}`}
    >
      {style.label}
    </span>
  )
}
