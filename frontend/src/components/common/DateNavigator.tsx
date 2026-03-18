import { useState, useCallback } from 'react'

interface DateNavigatorProps {
  selectedDate: string | null
  onDateChange: (date: string | null) => void
  /** Minimum date in YYYY-MM-DD format */
  minDate?: string
  /** Maximum date in YYYY-MM-DD format (defaults to today) */
  maxDate?: string
}

/** Quick-select presets for common lookback periods */
const PRESETS = [
  { label: 'Today', days: 0 },
  { label: '1W', days: 7 },
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
] as const

function formatDateISO(d: Date): string {
  return d.toISOString().split('T')[0]
}

function subtractDays(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return formatDateISO(d)
}

export default function DateNavigator({
  selectedDate,
  onDateChange,
  minDate = '2024-01-01',
  maxDate,
}: DateNavigatorProps): JSX.Element {
  const today = maxDate ?? formatDateISO(new Date())
  const isLive = selectedDate === null || selectedDate === today

  const [activePreset, setActivePreset] = useState<number>(0)

  const handlePresetClick = useCallback(
    (days: number) => {
      setActivePreset(days)
      if (days === 0) {
        onDateChange(null)
      } else {
        onDateChange(subtractDays(days))
      }
    },
    [onDateChange],
  )

  const handleDateInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value
      if (val === today) {
        setActivePreset(0)
        onDateChange(null)
      } else {
        setActivePreset(-1)
        onDateChange(val)
      }
    },
    [onDateChange, today],
  )

  const handleStepBack = useCallback(() => {
    const current = selectedDate ?? today
    const d = new Date(current)
    d.setDate(d.getDate() - 1)
    // Skip weekends
    while (d.getDay() === 0 || d.getDay() === 6) {
      d.setDate(d.getDate() - 1)
    }
    const newDate = formatDateISO(d)
    if (newDate >= minDate) {
      setActivePreset(-1)
      onDateChange(newDate)
    }
  }, [selectedDate, today, minDate, onDateChange])

  const handleStepForward = useCallback(() => {
    const current = selectedDate ?? today
    const d = new Date(current)
    d.setDate(d.getDate() + 1)
    // Skip weekends
    while (d.getDay() === 0 || d.getDay() === 6) {
      d.setDate(d.getDate() + 1)
    }
    const newDate = formatDateISO(d)
    if (newDate <= today) {
      if (newDate === today) {
        setActivePreset(0)
        onDateChange(null)
      } else {
        setActivePreset(-1)
        onDateChange(newDate)
      }
    }
  }, [selectedDate, today, onDateChange])

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-2.5">
      {/* Live indicator */}
      <div className="flex items-center gap-1.5">
        <span
          className={`inline-block h-2 w-2 rounded-full ${
            isLive ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'
          }`}
        />
        <span className="text-xs font-semibold text-slate-600">
          {isLive ? 'Live' : 'Historical'}
        </span>
      </div>

      {/* Preset buttons */}
      <div className="flex gap-1">
        {PRESETS.map((preset) => (
          <button
            key={preset.days}
            onClick={() => handlePresetClick(preset.days)}
            className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              activePreset === preset.days
                ? 'bg-teal-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* Step buttons + date picker */}
      <div className="flex items-center gap-1">
        <button
          onClick={handleStepBack}
          className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-600 hover:bg-slate-200"
          title="Previous trading day"
        >
          &#9664;
        </button>
        <input
          type="date"
          value={selectedDate ?? today}
          min={minDate}
          max={today}
          onChange={handleDateInput}
          className="rounded-md border border-slate-200 px-2 py-1 font-mono text-xs text-slate-700 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
        />
        <button
          onClick={handleStepForward}
          disabled={isLive}
          className={`rounded-md px-2 py-1 text-xs ${
            isLive
              ? 'cursor-not-allowed bg-slate-50 text-slate-300'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
          title="Next trading day"
        >
          &#9654;
        </button>
      </div>

      {/* Current date display */}
      <span className="font-mono text-xs text-slate-500">
        {selectedDate ?? today}
      </span>
    </div>
  )
}
