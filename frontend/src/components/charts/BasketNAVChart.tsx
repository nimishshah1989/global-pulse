import { useRef, useEffect, useCallback } from 'react'
import { select } from 'd3-selection'
import { scaleLinear, scaleTime } from 'd3-scale'
import { axisBottom, axisLeft } from 'd3-axis'
import { line as d3Line } from 'd3-shape'
import { extent } from 'd3-array'
import type { BasketNAV } from '@/types/baskets'

interface BasketNAVChartProps {
  data: BasketNAV[]
  width?: number
  height?: number
}

export default function BasketNAVChart({
  data,
  width = 600,
  height = 300,
}: BasketNAVChartProps): JSX.Element {
  const svgRef = useRef<SVGSVGElement>(null)

  const draw = useCallback(() => {
    if (!svgRef.current || data.length === 0) return

    const margin = { top: 20, right: 60, bottom: 35, left: 50 }
    const innerWidth = width - margin.left - margin.right
    const innerHeight = height - margin.top - margin.bottom

    const svg = select(svgRef.current)
    svg.selectAll('*').remove()

    const g = svg
      .attr('width', width)
      .attr('height', height)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`)

    const dates = data.map((d) => new Date(d.date))
    const allValues = data.flatMap((d) =>
      d.benchmark_nav !== null ? [d.nav, d.benchmark_nav] : [d.nav],
    )

    const dateExtent = extent(dates) as [Date, Date]
    const valExtent = extent(allValues) as [number, number]
    const padding = (valExtent[1] - valExtent[0]) * 0.1

    const xScale = scaleTime().domain(dateExtent).range([0, innerWidth])
    const yScale = scaleLinear()
      .domain([valExtent[0] - padding, valExtent[1] + padding])
      .range([innerHeight, 0])

    // Grid lines
    const yTicks = yScale.ticks(5)
    yTicks.forEach((tick) => {
      g.append('line')
        .attr('x1', 0).attr('x2', innerWidth)
        .attr('y1', yScale(tick)).attr('y2', yScale(tick))
        .attr('stroke', '#e2e8f0').attr('stroke-width', 1)
    })

    // Basket NAV line
    const navLine = d3Line<BasketNAV>()
      .x((d) => xScale(new Date(d.date)))
      .y((d) => yScale(d.nav))

    g.append('path')
      .datum(data)
      .attr('d', navLine)
      .attr('fill', 'none')
      .attr('stroke', '#0d9488')
      .attr('stroke-width', 2)

    // Benchmark line
    const hasBenchmark = data.some((d) => d.benchmark_nav !== null)
    if (hasBenchmark) {
      const benchLine = d3Line<BasketNAV>()
        .defined((d) => d.benchmark_nav !== null)
        .x((d) => xScale(new Date(d.date)))
        .y((d) => yScale(d.benchmark_nav ?? 0))

      g.append('path')
        .datum(data)
        .attr('d', benchLine)
        .attr('fill', 'none')
        .attr('stroke', '#94a3b8')
        .attr('stroke-width', 1.5)
        .attr('stroke-dasharray', '4,4')
    }

    // Axes
    const xAxis = axisBottom(xScale).ticks(6)
    const yAxis = axisLeft(yScale).ticks(5)

    g.append('g')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(xAxis)
      .selectAll('text')
      .attr('fill', '#64748b').attr('font-size', '10px')

    g.append('g')
      .call(yAxis)
      .selectAll('text')
      .attr('fill', '#64748b').attr('font-size', '10px')

    // Legend
    const legend = g.append('g').attr('transform', `translate(${innerWidth - 100}, 0)`)

    legend.append('line')
      .attr('x1', 0).attr('x2', 16).attr('y1', 0).attr('y2', 0)
      .attr('stroke', '#0d9488').attr('stroke-width', 2)
    legend.append('text')
      .attr('x', 20).attr('y', 4).attr('fill', '#475569').attr('font-size', '10px')
      .text('Basket')

    if (hasBenchmark) {
      legend.append('line')
        .attr('x1', 0).attr('x2', 16).attr('y1', 16).attr('y2', 16)
        .attr('stroke', '#94a3b8').attr('stroke-width', 1.5).attr('stroke-dasharray', '4,4')
      legend.append('text')
        .attr('x', 20).attr('y', 20).attr('fill', '#475569').attr('font-size', '10px')
        .text('Benchmark')
    }
  }, [data, width, height])

  useEffect(() => {
    draw()
  }, [draw])

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <h3 className="mb-2 text-sm font-semibold text-slate-700">NAV Performance</h3>
      <svg ref={svgRef} data-testid="basket-nav-chart" />
    </div>
  )
}
