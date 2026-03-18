import { memo, useCallback, useState } from 'react'
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  ZoomableGroup,
} from 'react-simple-maps'
import { useNavigate } from 'react-router-dom'
import { scaleSequential, interpolateRdYlGn } from 'd3'
import type { RankingItem } from '@/types/rs'

const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'

/** Approximate centroids for arrow placement (lon, lat) */
const COUNTRY_CENTROIDS: Record<string, [number, number]> = {
  US: [-98, 38],
  UK: [-2, 54],
  DE: [10, 51],
  FR: [2, 47],
  JP: [138, 36],
  HK: [114, 22],
  CN: [104, 35],
  KR: [128, 36],
  IN: [78, 22],
  TW: [121, 24],
  AU: [134, -25],
  BR: [-51, -14],
  CA: [-106, 56],
}

/** Returns arrow symbol, color class, and label based on RS momentum */
function getMomentumArrow(rsMomentumPct: number | null): {
  symbol: string
  colorClass: string
  fillColor: string
} {
  if (rsMomentumPct === null) {
    return { symbol: '\u25BA', colorClass: 'text-amber-500', fillColor: '#f59e0b' }
  }
  if (rsMomentumPct > 5) {
    return { symbol: '\u25B2', colorClass: 'text-emerald-600', fillColor: '#059669' }
  }
  if (rsMomentumPct < -5) {
    return { symbol: '\u25BC', colorClass: 'text-red-600', fillColor: '#dc2626' }
  }
  return { symbol: '\u25BA', colorClass: 'text-amber-500', fillColor: '#f59e0b' }
}

/**
 * Maps ISO 3166-1 numeric codes to our 2-letter country codes.
 * Only the 14 countries in our universe are mapped.
 */
const ISO_NUMERIC_TO_CODE: Record<string, string> = {
  '840': 'US',
  '826': 'UK',
  '276': 'DE',
  '250': 'FR',
  '392': 'JP',
  '344': 'HK',
  '156': 'CN',
  '410': 'KR',
  '356': 'IN',
  '158': 'TW',
  '036': 'AU',
  '076': 'BR',
  '124': 'CA',
}

/** Normalize country codes: backend uses 'UK', mock data uses 'GB' */
function normalizeCountryCode(code: string): string {
  return code === 'GB' ? 'UK' : code
}

const colorScale = scaleSequential(interpolateRdYlGn).domain([0, 100])

interface TooltipData {
  name: string
  score: number
  action: string
  rsMomentumPct: number | null
  priceTrend: string | null
  volumeCharacter: string | null
  x: number
  y: number
}

interface WorldChoroplethProps {
  data: RankingItem[]
}

function WorldChoroplethInner({ data }: WorldChoroplethProps): JSX.Element {
  const navigate = useNavigate()
  const [tooltip, setTooltip] = useState<TooltipData | null>(null)
  const [pulsingCountry, setPulsingCountry] = useState<string | null>(null)

  const scoreMap = new Map<string, RankingItem>()
  data.forEach((item) => {
    if (item.country) {
      scoreMap.set(normalizeCountryCode(item.country), item)
    }
  })

  const handleClick = useCallback(
    (countryCode: string) => {
      setPulsingCountry(countryCode)
      setTimeout(() => {
        setPulsingCountry(null)
        navigate(`/compass/country/${countryCode}`)
      }, 300)
    },
    [navigate],
  )

  return (
    <div className="relative w-full" data-testid="world-choropleth">
      <ComposableMap
        projectionConfig={{ scale: 147, center: [10, 5] }}
        className="w-full h-auto"
        style={{ maxHeight: '480px' }}
      >
        <ZoomableGroup>
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo) => {
                const isoNumeric = geo.id as string
                const countryCode = ISO_NUMERIC_TO_CODE[isoNumeric]
                const item = countryCode ? scoreMap.get(countryCode) : undefined
                const fillColor: string = item
                  ? (colorScale(item.rs_score) ?? '#e2e8f0')
                  : '#e2e8f0'

                const isPulsing = countryCode === pulsingCountry

                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill={fillColor}
                    stroke={isPulsing ? '#0d9488' : '#94a3b8'}
                    strokeWidth={isPulsing ? 2.5 : 0.5}
                    className={isPulsing ? 'animate-pulse' : ''}
                    style={{
                      default: {
                        outline: 'none',
                        transition: 'stroke-width 0.2s ease, stroke 0.2s ease',
                      },
                      hover: {
                        outline: 'none',
                        fill: item ? fillColor : '#cbd5e1' as string,
                        strokeWidth: item ? 1.5 : 0.5,
                        cursor: item ? 'pointer' : 'default',
                      },
                      pressed: { outline: 'none' },
                    }}
                    onClick={() => {
                      if (countryCode) handleClick(countryCode)
                    }}
                    onMouseEnter={(evt) => {
                      if (item) {
                        const target = evt.target as SVGElement
                        const rect = target.closest('svg')?.getBoundingClientRect()
                        setTooltip({
                          name: item.name,
                          score: item.rs_score,
                          action: item.action,
                          rsMomentumPct: item.rs_momentum_pct,
                          priceTrend: item.price_trend,
                          volumeCharacter: item.volume_character,
                          x: evt.clientX - (rect?.left ?? 0),
                          y: evt.clientY - (rect?.top ?? 0),
                        })
                      }
                    }}
                    onMouseLeave={() => setTooltip(null)}
                  />
                )
              })
            }
          </Geographies>
          {data.map((item) => {
            const code = item.country ? normalizeCountryCode(item.country) : null
            if (!code) return null
            const centroid = COUNTRY_CENTROIDS[code]
            if (!centroid) return null
            const arrow = getMomentumArrow(item.rs_momentum_pct)
            return (
              <Marker key={`arrow-${code}`} coordinates={centroid}>
                <text
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={10}
                  fontWeight="bold"
                  fill={arrow.fillColor}
                  style={{ pointerEvents: 'none', userSelect: 'none' }}
                >
                  {arrow.symbol}
                </text>
              </Marker>
            )
          })}
        </ZoomableGroup>
      </ComposableMap>

      {tooltip && (
        <div
          className="pointer-events-none absolute z-10 rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-lg"
          style={{
            left: tooltip.x + 12,
            top: tooltip.y - 10,
          }}
        >
          <p className="text-sm font-semibold text-slate-900">{tooltip.name}</p>
          <p className="text-xs text-slate-600">
            RS Score:{' '}
            <span className="font-mono font-medium">{tooltip.score.toFixed(1)}</span>
          </p>
          <p className="text-xs text-slate-600">Action: {tooltip.action}</p>
          <p className="text-xs text-slate-600">
            Momentum:{' '}
            <span
              className={`font-mono font-medium ${
                (tooltip.rsMomentumPct ?? 0) > 0
                  ? 'text-emerald-600'
                  : (tooltip.rsMomentumPct ?? 0) < 0
                    ? 'text-red-600'
                    : 'text-slate-600'
              }`}
            >
              {tooltip.rsMomentumPct !== null
                ? `${tooltip.rsMomentumPct > 0 ? '+' : ''}${tooltip.rsMomentumPct.toFixed(1)}%`
                : '-'}
            </span>
          </p>
          <p className="text-xs text-slate-600">
            Trend:{' '}
            <span
              className={`font-medium ${
                tooltip.priceTrend === 'OUTPERFORMING'
                  ? 'text-emerald-600'
                  : 'text-red-600'
              }`}
            >
              {tooltip.priceTrend ?? '-'}
            </span>
          </p>
          {tooltip.volumeCharacter && (
            <p className="text-xs text-slate-600">
              Volume: {tooltip.volumeCharacter}
            </p>
          )}
        </div>
      )}

      <div className="mt-2 flex items-center justify-center gap-2 text-xs text-slate-500">
        <span>Weak</span>
        <div
          className="h-3 w-48 rounded"
          style={{
            background: `linear-gradient(to right, ${colorScale(0)}, ${colorScale(50)}, ${colorScale(100)})`,
          }}
        />
        <span>Strong</span>
      </div>
    </div>
  )
}

const WorldChoropleth = memo(WorldChoroplethInner)
export default WorldChoropleth
