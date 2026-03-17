import { memo, useCallback, useState } from 'react'
import {
  ComposableMap,
  Geographies,
  Geography,
  ZoomableGroup,
} from 'react-simple-maps'
import { useNavigate } from 'react-router-dom'
import { scaleSequential, interpolateRdYlGn } from 'd3'
import type { RankingItem } from '@/types/rs'

const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'

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
  quadrant: string
  x: number
  y: number
}

interface WorldChoroplethProps {
  data: RankingItem[]
}

function WorldChoroplethInner({ data }: WorldChoroplethProps): JSX.Element {
  const navigate = useNavigate()
  const [tooltip, setTooltip] = useState<TooltipData | null>(null)

  const scoreMap = new Map<string, RankingItem>()
  data.forEach((item) => {
    if (item.country) {
      scoreMap.set(normalizeCountryCode(item.country), item)
    }
  })

  const handleClick = useCallback(
    (countryCode: string) => {
      navigate(`/compass/country/${countryCode}`)
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
                  ? (colorScale(item.adjusted_rs_score) ?? '#e2e8f0')
                  : '#e2e8f0'

                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill={fillColor}
                    stroke="#94a3b8"
                    strokeWidth={0.5}
                    style={{
                      default: { outline: 'none' },
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
                          score: item.adjusted_rs_score,
                          quadrant: item.quadrant,
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
          <p className="text-xs text-slate-600">Quadrant: {tooltip.quadrant}</p>
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
