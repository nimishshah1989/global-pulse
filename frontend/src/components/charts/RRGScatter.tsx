import { useRef, useEffect, useCallback, useState } from 'react'
import { select } from 'd3-selection'
import { scaleLinear } from 'd3-scale'
import { axisBottom, axisLeft } from 'd3-axis'
import { line as d3Line, curveCatmullRom } from 'd3-shape'
import type { RRGDataPoint } from '@/types/rs'

/** Visual quadrant on the RRG chart, determined by position (not the Action type) */
type Quadrant = 'LEADING' | 'WEAKENING' | 'LAGGING' | 'IMPROVING'

type TrailWeeksOption = 4 | 8 | 12

interface RRGScatterProps {
  data: RRGDataPoint[]
  width?: number
  height?: number
  onPointClick?: (id: string) => void
  trailWeeks?: TrailWeeksOption
}

const QUADRANT_BG: Record<Quadrant, string> = {
  LEADING: 'rgba(16, 185, 129, 0.06)',
  IMPROVING: 'rgba(59, 130, 246, 0.06)',
  WEAKENING: 'rgba(245, 158, 11, 0.06)',
  LAGGING: 'rgba(239, 68, 68, 0.06)',
}

const DOT_COLORS: Record<Quadrant, string> = {
  LEADING: '#059669',
  IMPROVING: '#2563eb',
  WEAKENING: '#d97706',
  LAGGING: '#dc2626',
}

const QUADRANT_META: Record<Quadrant, { icon: string; label: string }> = {
  LEADING: { icon: '\u2726', label: 'Leading' },
  WEAKENING: { icon: '\u25BC', label: 'Weakening' },
  LAGGING: { icon: '\u2715', label: 'Lagging' },
  IMPROVING: { icon: '\u25B2', label: 'Improving' },
}

const TRAIL_OPTIONS: TrailWeeksOption[] = [4, 8, 12]

function getQuadrant(rsScore: number, rsMomentum: number): Quadrant {
  if (rsScore > 50 && rsMomentum > 0) return 'LEADING'
  if (rsScore > 50 && rsMomentum <= 0) return 'WEAKENING'
  if (rsScore <= 50 && rsMomentum > 0) return 'IMPROVING'
  return 'LAGGING'
}

function shortenName(name: string): string {
  return name
    .replace(/Select Sector SPDR$/i, '')
    .replace(/Select Sector$/i, '')
    .replace(/ SPDR$/i, '')
    .replace(/ ETF$/i, '')
    .trim()
}

export default function RRGScatter({
  data,
  width = 600,
  height = 450,
  onPointClick,
  trailWeeks: initialTrailWeeks = 8,
}: RRGScatterProps): JSX.Element {
  const svgRef = useRef<SVGSVGElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const [trailWeeks, setTrailWeeks] = useState<TrailWeeksOption>(initialTrailWeeks)
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  const draw = useCallback(() => {
    if (!svgRef.current) return

    const margin = { top: 12, right: 20, bottom: 60, left: 52 }
    const innerWidth = width - margin.left - margin.right
    const innerHeight = height - margin.top - margin.bottom

    const svg = select(svgRef.current)
    svg.selectAll('*').remove()

    svg.attr('width', width).attr('height', height)

    // Defs for drop shadow
    const defs = svg.append('defs')
    const filter = defs.append('filter').attr('id', 'dot-shadow')
    filter.append('feDropShadow')
      .attr('dx', 0).attr('dy', 1)
      .attr('stdDeviation', 2)
      .attr('flood-color', 'rgba(0,0,0,0.2)')

    const g = svg
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`)

    const xScale = scaleLinear().domain([0, 100]).range([0, innerWidth])
    const yScale = scaleLinear().domain([-50, 50]).range([innerHeight, 0])

    // --- Quadrant backgrounds ---
    g.append('rect')
      .attr('x', 0).attr('y', 0)
      .attr('width', xScale(50)).attr('height', yScale(0))
      .attr('fill', QUADRANT_BG.IMPROVING)

    g.append('rect')
      .attr('x', xScale(50)).attr('y', 0)
      .attr('width', innerWidth - xScale(50)).attr('height', yScale(0))
      .attr('fill', QUADRANT_BG.LEADING)

    g.append('rect')
      .attr('x', 0).attr('y', yScale(0))
      .attr('width', xScale(50)).attr('height', innerHeight - yScale(0))
      .attr('fill', QUADRANT_BG.LAGGING)

    g.append('rect')
      .attr('x', xScale(50)).attr('y', yScale(0))
      .attr('width', innerWidth - xScale(50)).attr('height', innerHeight - yScale(0))
      .attr('fill', QUADRANT_BG.WEAKENING)

    // --- Grid lines ---
    const xGridValues = [10, 20, 30, 40, 60, 70, 80, 90]
    const yGridValues = [-40, -30, -20, -10, 10, 20, 30, 40]

    xGridValues.forEach((v) => {
      g.append('line')
        .attr('x1', xScale(v)).attr('y1', 0)
        .attr('x2', xScale(v)).attr('y2', innerHeight)
        .attr('stroke', '#e2e8f0')
        .attr('stroke-width', 0.5)
    })

    yGridValues.forEach((v) => {
      g.append('line')
        .attr('x1', 0).attr('y1', yScale(v))
        .attr('x2', innerWidth).attr('y2', yScale(v))
        .attr('stroke', '#e2e8f0')
        .attr('stroke-width', 0.5)
    })

    // --- Center divider lines ---
    g.append('line')
      .attr('x1', xScale(50)).attr('y1', 0)
      .attr('x2', xScale(50)).attr('y2', innerHeight)
      .attr('stroke', '#94a3b8').attr('stroke-width', 1).attr('stroke-dasharray', '6,3')

    g.append('line')
      .attr('x1', 0).attr('y1', yScale(0))
      .attr('x2', innerWidth).attr('y2', yScale(0))
      .attr('stroke', '#94a3b8').attr('stroke-width', 1).attr('stroke-dasharray', '6,3')

    // --- Quadrant labels with icons ---
    const labelPad = 10
    const quadrantLabelPositions: { quadrant: Quadrant; x: number; y: number; anchor: string }[] = [
      {
        quadrant: 'IMPROVING',
        x: labelPad,
        y: labelPad + 14,
        anchor: 'start',
      },
      {
        quadrant: 'LEADING',
        x: innerWidth - labelPad,
        y: labelPad + 14,
        anchor: 'end',
      },
      {
        quadrant: 'LAGGING',
        x: labelPad,
        y: innerHeight - labelPad,
        anchor: 'start',
      },
      {
        quadrant: 'WEAKENING',
        x: innerWidth - labelPad,
        y: innerHeight - labelPad,
        anchor: 'end',
      },
    ]

    quadrantLabelPositions.forEach(({ quadrant, x, y, anchor }) => {
      const meta = QUADRANT_META[quadrant]
      const color = DOT_COLORS[quadrant]
      g.append('text')
        .attr('x', x)
        .attr('y', y)
        .attr('text-anchor', anchor)
        .attr('fill', color)
        .attr('font-size', '10px')
        .attr('font-weight', '600')
        .attr('opacity', 0.6)
        .text(`${meta.icon} ${meta.label}`)
    })

    // --- Axes ---
    const xAxis = axisBottom(xScale).ticks(10).tickSize(-4)
    const yAxis = axisLeft(yScale).ticks(10).tickSize(-4)

    const xAxisG = g.append('g')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(xAxis)

    xAxisG.select('.domain').attr('stroke', '#cbd5e1')
    xAxisG.selectAll('.tick text')
      .attr('fill', '#64748b')
      .attr('font-size', '9px')
    xAxisG.selectAll('.tick line').attr('stroke', '#cbd5e1')

    const yAxisG = g.append('g').call(yAxis)
    yAxisG.select('.domain').attr('stroke', '#cbd5e1')
    yAxisG.selectAll('.tick text')
      .attr('fill', '#64748b')
      .attr('font-size', '9px')
    yAxisG.selectAll('.tick line').attr('stroke', '#cbd5e1')

    // Axis labels
    g.append('text')
      .attr('x', innerWidth / 2).attr('y', innerHeight + 36)
      .attr('text-anchor', 'middle')
      .attr('fill', '#475569').attr('font-size', '11px').attr('font-weight', '500')
      .text('RS Score')

    g.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('x', -innerHeight / 2).attr('y', -38)
      .attr('text-anchor', 'middle')
      .attr('fill', '#475569').attr('font-size', '11px').attr('font-weight', '500')
      .text('RS Momentum')

    // --- Trail and dot rendering ---
    // Limit trail points based on trailWeeks (approx 5 trading days per week)
    const maxTrailPoints = trailWeeks * 5

    const trailLine = d3Line<{ rs_score: number; rs_momentum: number }>()
      .x((d) => xScale(d.rs_score))
      .y((d) => yScale(d.rs_momentum))
      .curve(curveCatmullRom.alpha(0.5))

    // Collision-free label positioning
    const labelPositions: { x: number; y: number; w: number; h: number }[] = []

    function findNonOverlappingPosition(
      cx: number,
      cy: number,
      textWidth: number,
    ): { lx: number; ly: number } {
      const h = 12
      const offsets = [
        { dx: 11, dy: 4 },
        { dx: 11, dy: -8 },
        { dx: 11, dy: 16 },
        { dx: -(textWidth + 11), dy: 4 },
        { dx: -(textWidth + 11), dy: -8 },
        { dx: -(textWidth + 11), dy: 16 },
        { dx: -textWidth / 2, dy: -14 },
        { dx: -textWidth / 2, dy: 20 },
      ]

      for (const { dx, dy } of offsets) {
        const lx = cx + dx
        const ly = cy + dy
        const rect = { x: lx, y: ly - h, w: textWidth, h }
        const overlaps = labelPositions.some(
          (p) =>
            rect.x < p.x + p.w &&
            rect.x + rect.w > p.x &&
            rect.y < p.y + p.h &&
            rect.y + rect.h > p.y,
        )
        if (
          !overlaps &&
          lx >= 0 &&
          lx + textWidth <= innerWidth &&
          ly >= 0 &&
          ly <= innerHeight
        ) {
          labelPositions.push(rect)
          return { lx, ly }
        }
      }
      const fallback = { x: cx + 11, y: cy + 4 - h, w: textWidth, h }
      labelPositions.push(fallback)
      return { lx: cx + 11, ly: cy + 4 }
    }

    // Draw each data point's trail + dot
    data.forEach((point) => {
      const quadrant = getQuadrant(point.rs_score, point.rs_momentum)
      const color = DOT_COLORS[quadrant]
      const trail = point.trail.slice(-maxTrailPoints)
      const isHovered = hoveredId === point.id
      const isDimmed = hoveredId !== null && hoveredId !== point.id
      const groupOpacity = isDimmed ? 0.12 : 1

      const pointGroup = g.append('g')
        .attr('class', `rrg-point-group rrg-point-${point.id}`)
        .attr('opacity', groupOpacity)

      // Trail line (smooth curve)
      if (trail.length > 1) {
        pointGroup.append('path')
          .datum(trail)
          .attr('d', trailLine)
          .attr('fill', 'none')
          .attr('stroke', color)
          .attr('stroke-width', isHovered ? 2 : 1.5)
          .attr('opacity', isHovered ? 0.7 : 0.35)
          .attr('stroke-linecap', 'round')
      }

      // Trail dots with fade
      trail.forEach((tp, i) => {
        const isLast = i === trail.length - 1
        if (isLast) return // Current position drawn separately

        const normalizedAge = trail.length > 1 ? i / (trail.length - 1) : 0
        const dotOpacity = 0.1 + normalizedAge * 0.6

        pointGroup.append('circle')
          .attr('cx', xScale(tp.rs_score))
          .attr('cy', yScale(tp.rs_momentum))
          .attr('r', 2.5)
          .attr('fill', color)
          .attr('opacity', isHovered ? dotOpacity + 0.2 : dotOpacity)
      })

      // Current position dot
      const cx = xScale(point.rs_score)
      const cy = yScale(point.rs_momentum)

      const dotG = pointGroup.append('g')
        .style('cursor', onPointClick ? 'pointer' : 'default')

      // White border ring + shadow
      dotG.append('circle')
        .attr('cx', cx)
        .attr('cy', cy)
        .attr('r', 7)
        .attr('fill', color)
        .attr('stroke', '#ffffff')
        .attr('stroke-width', 2)
        .attr('filter', 'url(#dot-shadow)')

      // Invisible larger hit area for hover
      dotG.append('circle')
        .attr('cx', cx)
        .attr('cy', cy)
        .attr('r', 14)
        .attr('fill', 'transparent')
        .attr('stroke', 'none')
        .on('mouseenter', (event: MouseEvent) => {
          setHoveredId(point.id)
          showTooltip(event, point)
        })
        .on('mousemove', (event: MouseEvent) => {
          moveTooltip(event)
        })
        .on('mouseleave', () => {
          setHoveredId(null)
          hideTooltip()
        })
        .on('click', () => {
          if (onPointClick) onPointClick(point.id)
        })

      // Label
      const shortName = shortenName(point.name)
      const estWidth = shortName.length * 5.5
      const { lx, ly } = findNonOverlappingPosition(cx, cy, estWidth)

      pointGroup.append('text')
        .attr('x', lx)
        .attr('y', ly)
        .attr('fill', isDimmed ? '#94a3b8' : '#334155')
        .attr('font-size', '10px')
        .attr('font-weight', '500')
        .attr('pointer-events', 'none')
        .text(shortName)
    })

    function showTooltip(event: MouseEvent, point: RRGDataPoint): void {
      const tooltip = tooltipRef.current
      if (!tooltip) return

      const pointQuadrant = getQuadrant(point.rs_score, point.rs_momentum)
      const quadMeta = QUADRANT_META[pointQuadrant]
      const quadColor = DOT_COLORS[pointQuadrant]

      tooltip.innerHTML = `
        <div style="font-weight:600;font-size:13px;margin-bottom:4px;color:#0f172a;">
          ${shortenName(point.name)}
        </div>
        <div style="display:grid;grid-template-columns:auto auto;gap:2px 12px;font-size:11px;">
          <span style="color:#64748b;">RS Score</span>
          <span style="font-weight:600;font-variant-numeric:tabular-nums;">${point.rs_score.toFixed(1)}</span>
          <span style="color:#64748b;">RS Momentum</span>
          <span style="font-weight:600;font-variant-numeric:tabular-nums;">${point.rs_momentum > 0 ? '+' : ''}${point.rs_momentum.toFixed(1)}</span>
          <span style="color:#64748b;">Quadrant</span>
          <span style="color:${quadColor};font-weight:600;">${quadMeta.icon} ${quadMeta.label}</span>
        </div>
      `
      tooltip.style.opacity = '1'
      tooltip.style.pointerEvents = 'none'
      positionTooltip(event, tooltip)
    }

    function moveTooltip(event: MouseEvent): void {
      const tooltip = tooltipRef.current
      if (!tooltip) return
      positionTooltip(event, tooltip)
    }

    function positionTooltip(event: MouseEvent, tooltip: HTMLDivElement): void {
      const containerRect = svgRef.current?.getBoundingClientRect()
      if (!containerRect) return

      let left = event.clientX - containerRect.left + 14
      let top = event.clientY - containerRect.top - 10

      // Prevent overflow right
      if (left + 180 > width) {
        left = event.clientX - containerRect.left - 190
      }
      // Prevent overflow bottom
      if (top + 100 > height) {
        top = event.clientY - containerRect.top - 100
      }

      tooltip.style.left = `${left}px`
      tooltip.style.top = `${top}px`
    }

    function hideTooltip(): void {
      const tooltip = tooltipRef.current
      if (!tooltip) return
      tooltip.style.opacity = '0'
    }
  }, [data, width, height, onPointClick, trailWeeks, hoveredId])

  useEffect(() => {
    draw()
  }, [draw])

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      {/* Time period selector */}
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700">
          Relative Rotation Graph
        </h3>
        <div className="flex gap-1">
          {TRAIL_OPTIONS.map((w) => (
            <button
              key={w}
              onClick={() => setTrailWeeks(w)}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                trailWeeks === w
                  ? 'bg-teal-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {w}W
            </button>
          ))}
        </div>
      </div>

      {/* Chart container */}
      <div className="relative">
        <svg ref={svgRef} data-testid="rrg-scatter" />
        <div
          ref={tooltipRef}
          className="pointer-events-none absolute rounded-lg border border-slate-200 bg-white px-3 py-2 opacity-0 shadow-lg transition-opacity duration-150"
          style={{ zIndex: 50, minWidth: 160 }}
        />
      </div>

      {/* Legend */}
      <div className="mt-3 flex flex-wrap items-center justify-center gap-x-5 gap-y-1">
        {(
          ['LEADING', 'WEAKENING', 'LAGGING', 'IMPROVING'] as Quadrant[]
        ).map((q) => {
          const meta = QUADRANT_META[q]
          const color = DOT_COLORS[q]
          return (
            <div key={q} className="flex items-center gap-1.5 text-xs">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="font-medium text-slate-600">
                {meta.icon} {meta.label}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
