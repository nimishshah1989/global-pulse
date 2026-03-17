import { useEffect, useRef } from 'react'
import { createChart, type IChartApi, type ISeriesApi, LineSeries, HistogramSeries, type LineData, type HistogramData, type Time } from 'lightweight-charts'

interface RSLineDataPoint {
  date: string
  rs_line: number
  rs_ma_150: number
  volume: number
}

interface RSLineChartProps {
  data: RSLineDataPoint[]
  title?: string
}

export default function RSLineChart({ data, title }: RSLineChartProps): JSX.Element {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartApiRef = useRef<IChartApi | null>(null)
  const rsSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const maSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const volSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)

  useEffect(() => {
    if (!chartRef.current || data.length === 0) return

    const chart = createChart(chartRef.current, {
      layout: {
        background: { color: '#ffffff' },
        textColor: '#64748b',
        fontFamily: 'Inter, system-ui, sans-serif',
      },
      grid: {
        vertLines: { color: '#f1f5f9' },
        horzLines: { color: '#f1f5f9' },
      },
      width: chartRef.current.clientWidth,
      height: 300,
      rightPriceScale: {
        borderColor: '#e2e8f0',
      },
      timeScale: {
        borderColor: '#e2e8f0',
        timeVisible: false,
      },
    })

    chartApiRef.current = chart

    const rsSeries = chart.addSeries(LineSeries, {
      color: '#2563eb',
      lineWidth: 2,
      title: 'RS Line',
      priceScaleId: 'right',
    })
    rsSeriesRef.current = rsSeries

    const maSeries = chart.addSeries(LineSeries, {
      color: '#f97316',
      lineWidth: 1,
      lineStyle: 2,
      title: '150-day MA',
      priceScaleId: 'right',
    })
    maSeriesRef.current = maSeries

    const volSeries = chart.addSeries(HistogramSeries, {
      color: '#94a3b8',
      priceScaleId: 'volume',
      priceFormat: { type: 'volume' },
    })
    volSeriesRef.current = volSeries

    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })

    const rsData: LineData[] = data.map((d) => ({
      time: d.date as Time,
      value: d.rs_line,
    }))

    const maData: LineData[] = data.map((d) => ({
      time: d.date as Time,
      value: d.rs_ma_150,
    }))

    const volData: HistogramData[] = data.map((d, i) => ({
      time: d.date as Time,
      value: d.volume,
      color: i > 0 && d.rs_line >= data[i - 1].rs_line ? '#bbf7d0' : '#fecaca',
    }))

    rsSeries.setData(rsData)
    maSeries.setData(maData)
    volSeries.setData(volData)

    chart.timeScale().fitContent()

    const handleResize = (): void => {
      if (chartRef.current) {
        chart.applyOptions({ width: chartRef.current.clientWidth })
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
      chartApiRef.current = null
      rsSeriesRef.current = null
      maSeriesRef.current = null
      volSeriesRef.current = null
    }
  }, [data])

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      {title && (
        <h3 className="mb-3 text-sm font-semibold text-slate-700">{title}</h3>
      )}
      <div ref={chartRef} data-testid="rs-line-chart" />
    </div>
  )
}
