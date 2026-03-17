import { useRef, useEffect, useCallback } from 'react'
import { select } from 'd3-selection'
import { scaleLinear } from 'd3-scale'
import { axisBottom, axisLeft } from 'd3-axis'
import { line as d3Line } from 'd3-shape'
import type { RRGDataPoint, Quadrant } from '@/types/rs'

interface RRGScatterProps {
  data: RRGDataPoint[]
  width?: number
  height?: number
  onPointClick?: (id: string) => void
}

const QUADRANT_COLORS: Record<Quadrant, string> = {
  LEADING: 'rgba(16, 185, 129, 0.08)',
  IMPROVING: 'rgba(59, 130, 246, 0.08)',
  WEAKENING: 'rgba(245, 158, 11, 0.08)',
  LAGGING: 'rgba(239, 68, 68, 0.08)',
}

const DOT_COLORS: Record<Quadrant, string> = {
  LEADING: '#059669',
  IMPROVING: '#2563eb',
  WEAKENING: '#d97706',
  LAGGING: '#dc2626',
}

const QUADRANT_LABELS: { label: string; x: 'left' | 'right'; y: 'top' | 'bottom' }[] = [
  { label: 'IMPROVING', x: 'left', y: 'top' },
  { label: 'LEADING', x: 'right', y: 'top' },
  { label: 'LAGGING', x: 'left', y: 'bottom' },
  { label: 'WEAKENING', x: 'right', y: 'bottom' },
]

export default function RRGScatter({
  data,
  width = 600,
  height = 450,
  onPointClick,
}: RRGScatterProps): JSX.Element {
  const svgRef = useRef<SVGSVGElement>(null)

  const draw = useCallback(() => {
    if (!svgRef.current) return

    const margin = { top: 30, right: 30, bottom: 40, left: 50 }
    const innerWidth = width - margin.left - margin.right
    const innerHeight = height - margin.top - margin.bottom

    const svg = select(svgRef.current)
    svg.selectAll('*').remove()

    const g = svg
      .attr('width', width)
      .attr('height', height)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`)

    const xScale = scaleLinear().domain([0, 100]).range([0, innerWidth])
    const yScale = scaleLinear().domain([-50, 50]).range([innerHeight, 0])

    // Quadrant backgrounds
    // Top-left: IMPROVING
    g.append('rect')
      .attr('x', 0).attr('y', 0)
      .attr('width', xScale(50)).attr('height', yScale(0))
      .attr('fill', QUADRANT_COLORS.IMPROVING)

    // Top-right: LEADING
    g.append('rect')
      .attr('x', xScale(50)).attr('y', 0)
      .attr('width', innerWidth - xScale(50)).attr('height', yScale(0))
      .attr('fill', QUADRANT_COLORS.LEADING)

    // Bottom-left: LAGGING
    g.append('rect')
      .attr('x', 0).attr('y', yScale(0))
      .attr('width', xScale(50)).attr('height', innerHeight - yScale(0))
      .attr('fill', QUADRANT_COLORS.LAGGING)

    // Bottom-right: WEAKENING
    g.append('rect')
      .attr('x', xScale(50)).attr('y', yScale(0))
      .attr('width', innerWidth - xScale(50)).attr('height', innerHeight - yScale(0))
      .attr('fill', QUADRANT_COLORS.WEAKENING)

    // Center lines
    g.append('line')
      .attr('x1', xScale(50)).attr('y1', 0)
      .attr('x2', xScale(50)).attr('y2', innerHeight)
      .attr('stroke', '#94a3b8').attr('stroke-width', 1).attr('stroke-dasharray', '4,4')

    g.append('line')
      .attr('x1', 0).attr('y1', yScale(0))
      .attr('x2', innerWidth).attr('y2', yScale(0))
      .attr('stroke', '#94a3b8').attr('stroke-width', 1).attr('stroke-dasharray', '4,4')

    // Quadrant labels
    const labelPad = 8
    QUADRANT_LABELS.forEach(({ label, x, y }) => {
      g.append('text')
        .attr('x', x === 'left' ? labelPad : innerWidth - labelPad)
        .attr('y', y === 'top' ? labelPad + 12 : innerHeight - labelPad)
        .attr('text-anchor', x === 'left' ? 'start' : 'end')
        .attr('fill', '#94a3b8')
        .attr('font-size', '10px')
        .attr('font-weight', '600')
        .text(label)
    })

    // Axes
    const xAxis = axisBottom(xScale).ticks(10)
    const yAxis = axisLeft(yScale).ticks(10)

    g.append('g')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(xAxis)
      .selectAll('text')
      .attr('fill', '#64748b')
      .attr('font-size', '10px')

    g.append('g')
      .call(yAxis)
      .selectAll('text')
      .attr('fill', '#64748b')
      .attr('font-size', '10px')

    // Axis labels
    g.append('text')
      .attr('x', innerWidth / 2).attr('y', innerHeight + 35)
      .attr('text-anchor', 'middle')
      .attr('fill', '#475569').attr('font-size', '11px').attr('font-weight', '500')
      .text('RS Score')

    g.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('x', -innerHeight / 2).attr('y', -38)
      .attr('text-anchor', 'middle')
      .attr('fill', '#475569').attr('font-size', '11px').attr('font-weight', '500')
      .text('RS Momentum')

    // Trail line generator
    const trailLine = d3Line<{ rs_score: number; rs_momentum: number }>()
      .x((d) => xScale(d.rs_score))
      .y((d) => yScale(d.rs_momentum))

    // Collect label positions for collision detection
    const labelPositions: { x: number; y: number; w: number; h: number }[] = []

    function findNonOverlappingPosition(
      cx: number,
      cy: number,
      textWidth: number,
    ): { lx: number; ly: number } {
      const h = 12
      // Try 8 directions: right, top-right, top, top-left, left, bottom-left, bottom, bottom-right
      const offsets = [
        { dx: 9, dy: 4 },
        { dx: 9, dy: -8 },
        { dx: 9, dy: 14 },
        { dx: -(textWidth + 9), dy: 4 },
        { dx: -(textWidth + 9), dy: -8 },
        { dx: -(textWidth + 9), dy: 14 },
        { dx: -textWidth / 2, dy: -12 },
        { dx: -textWidth / 2, dy: 18 },
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
        if (!overlaps && lx >= 0 && lx + textWidth <= innerWidth && ly >= 0 && ly <= innerHeight) {
          labelPositions.push(rect)
          return { lx, ly }
        }
      }
      // Fallback: default right
      const fallback = { x: cx + 9, y: cy + 4 - h, w: textWidth, h }
      labelPositions.push(fallback)
      return { lx: cx + 9, ly: cy + 4 }
    }

    // Shorten long names for cleaner chart
    function shortenName(name: string): string {
      return name
        .replace(/Select Sector SPDR$/i, '')
        .replace(/Select Sector$/i, '')
        .replace(/ SPDR$/i, '')
        .replace(/ ETF$/i, '')
        .trim()
    }

    // Draw trails and dots
    data.forEach((point) => {
      const color = DOT_COLORS[point.quadrant]

      if (point.trail.length > 1) {
        g.append('path')
          .datum(point.trail)
          .attr('d', trailLine)
          .attr('fill', 'none')
          .attr('stroke', color)
          .attr('stroke-width', 1.5)
          .attr('opacity', 0.4)
      }

      // Trail dots (fading)
      point.trail.forEach((tp, i) => {
        if (i < point.trail.length - 1) {
          g.append('circle')
            .attr('cx', xScale(tp.rs_score))
            .attr('cy', yScale(tp.rs_momentum))
            .attr('r', 2)
            .attr('fill', color)
            .attr('opacity', 0.15 + (i / point.trail.length) * 0.35)
        }
      })

      // Main dot
      const dotGroup = g.append('g')
        .style('cursor', onPointClick ? 'pointer' : 'default')

      dotGroup.on('click', () => {
        if (onPointClick) onPointClick(point.id)
      })

      const cx = xScale(point.rs_score)
      const cy = yScale(point.rs_momentum)

      dotGroup.append('circle')
        .attr('cx', cx)
        .attr('cy', cy)
        .attr('r', 6)
        .attr('fill', color)
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5)

      // Label with collision avoidance
      const shortName = shortenName(point.name)
      const estWidth = shortName.length * 5.5
      const { lx, ly } = findNonOverlappingPosition(cx, cy, estWidth)

      dotGroup.append('text')
        .attr('x', lx)
        .attr('y', ly)
        .attr('fill', '#1e293b')
        .attr('font-size', '10px')
        .attr('font-weight', '500')
        .text(shortName)
    })
  }, [data, width, height, onPointClick])

  useEffect(() => {
    draw()
  }, [draw])

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <svg ref={svgRef} data-testid="rrg-scatter" />
    </div>
  )
}
