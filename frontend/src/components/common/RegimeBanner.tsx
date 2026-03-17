import type { Regime } from '@/types/rs'

interface RegimeBannerProps {
  regime: Regime
}

export default function RegimeBanner({ regime }: RegimeBannerProps): JSX.Element {
  if (regime === 'RISK_ON') {
    return (
      <div className="w-full rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-2 text-sm font-medium text-emerald-800">
        RISK ON — Global benchmark above 200-day MA
      </div>
    )
  }

  return (
    <div className="w-full rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-sm font-medium text-red-800">
      RISK OFF — Global benchmark below 200-day MA. Defensive positioning recommended.
    </div>
  )
}
