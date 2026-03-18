import { useEffect, useState } from 'react'

/* ---------- Section wrapper ---------- */
export function Section({
  id,
  title,
  children,
}: {
  id: string
  title: string
  children: React.ReactNode
}): JSX.Element {
  return (
    <section id={id} className="scroll-mt-24 rounded-xl border border-slate-200 bg-white p-6">
      <h2 className="mb-4 text-lg font-bold text-slate-900">{title}</h2>
      <div className="text-sm leading-relaxed text-slate-700">{children}</div>
    </section>
  )
}

/* ---------- Styled code block ---------- */
export function Code({ children }: { children: React.ReactNode }): JSX.Element {
  return (
    <code className="mt-1 block rounded-lg bg-slate-100 px-3 py-2 font-mono text-xs text-slate-800">
      {children}
    </code>
  )
}

/* ---------- Example callout ---------- */
export function Example({ children }: { children: React.ReactNode }): JSX.Element {
  return (
    <div className="mt-2 rounded-lg border border-teal-200 bg-teal-50 px-3 py-2">
      <span className="text-[10px] font-bold uppercase tracking-wider text-teal-600">Example</span>
      <p className="mt-0.5 font-mono text-xs text-teal-800">{children}</p>
    </div>
  )
}

/* ---------- Hierarchy card ---------- */
export function HierarchyCard({
  level,
  emoji,
  title,
  description,
  color,
}: {
  level: number
  emoji: string
  title: string
  description: string
  color: string
}): JSX.Element {
  return (
    <div className={`rounded-xl border p-4 ${color}`}>
      <div className="mb-1 text-xs font-bold uppercase tracking-wider text-slate-500">
        Level {level}
      </div>
      <h4 className="font-semibold text-slate-800">{emoji} {title}</h4>
      <p className="mt-1 text-xs text-slate-600">{description}</p>
    </div>
  )
}

/* ---------- Signal card ---------- */
export function SignalCard({
  name,
  description,
  conviction,
}: {
  name: string
  description: string
  conviction: string
}): JSX.Element {
  const colors: Record<string, string> = {
    'Very High': 'bg-emerald-100 text-emerald-800',
    High: 'bg-emerald-50 text-emerald-700',
    Medium: 'bg-amber-50 text-amber-700',
    Caution: 'bg-red-50 text-red-700',
    Critical: 'bg-red-100 text-red-800',
  }
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between">
        <h4 className="font-semibold text-slate-800">{name}</h4>
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${colors[conviction] ?? 'bg-slate-100 text-slate-600'}`}>
          {conviction}
        </span>
      </div>
      <p className="mt-1 text-xs text-slate-600">{description}</p>
    </div>
  )
}

/* ---------- Weight bar for composite weights ---------- */
export function WeightBar(): JSX.Element {
  const segments = [
    { label: '1M', w: 10, color: 'bg-sky-400' },
    { label: '3M', w: 25, color: 'bg-teal-400' },
    { label: '6M', w: 35, color: 'bg-teal-600' },
    { label: '12M', w: 30, color: 'bg-teal-800' },
  ]
  return (
    <div className="mt-2">
      <div className="flex h-7 overflow-hidden rounded-lg">
        {segments.map((s) => (
          <div
            key={s.label}
            className={`${s.color} flex items-center justify-center text-[10px] font-bold text-white`}
            style={{ width: `${s.w}%` }}
          >
            {s.label}: {s.w}%
          </div>
        ))}
      </div>
    </div>
  )
}

/* ---------- Volume multiplier curve SVG ---------- */
export function VolumeMultiplierCurve(): JSX.Element {
  return (
    <div className="mt-3 flex justify-center">
      <svg viewBox="0 0 300 120" className="w-full max-w-sm" aria-label="Volume multiplier curve">
        {/* axes */}
        <line x1="40" y1="10" x2="40" y2="100" stroke="#94a3b8" strokeWidth="1" />
        <line x1="40" y1="100" x2="290" y2="100" stroke="#94a3b8" strokeWidth="1" />
        {/* y labels */}
        <text x="4" y="15" className="fill-slate-500" fontSize="8">1.15</text>
        <text x="4" y="55" className="fill-slate-500" fontSize="8">1.00</text>
        <text x="4" y="95" className="fill-slate-500" fontSize="8">0.85</text>
        {/* x labels */}
        <text x="55" y="112" className="fill-slate-500" fontSize="8">0.0</text>
        <text x="115" y="112" className="fill-slate-500" fontSize="8">0.5</text>
        <text x="175" y="112" className="fill-slate-500" fontSize="8">1.0</text>
        <text x="235" y="112" className="fill-slate-500" fontSize="8">1.5+</text>
        {/* curve: flat 0.85 from 0-0.5, flat 1.0 from 0.5-1.0, linear to 1.15 from 1.0-1.5 */}
        <polyline
          points="60,90 120,90 120,50 180,50 240,13 280,13"
          fill="none"
          stroke="#0d9488"
          strokeWidth="2.5"
          strokeLinejoin="round"
        />
        {/* neutral line */}
        <line x1="40" y1="50" x2="290" y2="50" stroke="#94a3b8" strokeWidth="0.5" strokeDasharray="4" />
        {/* zone labels */}
        <text x="70" y="82" className="fill-red-500" fontSize="7" fontWeight="bold">Discount</text>
        <text x="130" y="44" className="fill-slate-500" fontSize="7" fontWeight="bold">Neutral</text>
        <text x="220" y="8" className="fill-emerald-600" fontSize="7" fontWeight="bold">Boost</text>
        <text x="100" y="118" className="fill-slate-400" fontSize="7">Volume Ratio</text>
      </svg>
    </div>
  )
}

/* ---------- RRG Quadrant Diagram ---------- */
export function RRGDiagram(): JSX.Element {
  return (
    <div className="flex justify-center">
      <svg viewBox="0 0 320 280" className="w-full max-w-md" aria-label="RRG quadrant diagram with rotation arrows">
        {/* quadrant backgrounds */}
        <rect x="160" y="10" width="150" height="120" rx="8" fill="#ecfdf5" stroke="#a7f3d0" />
        <rect x="160" y="130" width="150" height="120" rx="8" fill="#fef3c7" stroke="#fde68a" />
        <rect x="10" y="130" width="150" height="120" rx="8" fill="#fef2f2" stroke="#fecaca" />
        <rect x="10" y="10" width="150" height="120" rx="8" fill="#eff6ff" stroke="#bfdbfe" />
        {/* axis labels */}
        <text x="160" y="268" textAnchor="middle" className="fill-slate-400" fontSize="9">RS Score (50 = center)</text>
        <text x="6" y="136" textAnchor="middle" className="fill-slate-400" fontSize="9" transform="rotate(-90,6,136)">RS Momentum</text>
        {/* axis lines */}
        <line x1="160" y1="10" x2="160" y2="250" stroke="#cbd5e1" strokeWidth="1.5" strokeDasharray="4" />
        <line x1="10" y1="130" x2="310" y2="130" stroke="#cbd5e1" strokeWidth="1.5" strokeDasharray="4" />
        {/* quadrant labels */}
        <text x="85" y="45" textAnchor="middle" fontSize="13" fontWeight="bold" className="fill-blue-600">IMPROVING</text>
        <text x="85" y="60" textAnchor="middle" fontSize="8" className="fill-blue-500">RS &lt; 50, Mom &gt; 0</text>
        <text x="235" y="45" textAnchor="middle" fontSize="13" fontWeight="bold" className="fill-emerald-700">LEADING</text>
        <text x="235" y="60" textAnchor="middle" fontSize="8" className="fill-emerald-600">RS &gt; 50, Mom &gt; 0</text>
        <text x="235" y="175" textAnchor="middle" fontSize="13" fontWeight="bold" className="fill-amber-700">WEAKENING</text>
        <text x="235" y="190" textAnchor="middle" fontSize="8" className="fill-amber-600">RS &gt; 50, Mom &le; 0</text>
        <text x="85" y="175" textAnchor="middle" fontSize="13" fontWeight="bold" className="fill-red-700">LAGGING</text>
        <text x="85" y="190" textAnchor="middle" fontSize="8" className="fill-red-600">RS &le; 50, Mom &le; 0</text>
        {/* clockwise rotation arrow path */}
        <path
          d="M 200,75 A 70,55 0 0,1 265,155 A 70,55 0 0,1 200,210 A 70,55 0 0,1 110,155 A 70,55 0 0,1 155,80"
          fill="none" stroke="#475569" strokeWidth="1.5" strokeDasharray="6,3"
          markerEnd="url(#arrowhead)"
        />
        <defs>
          <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="#475569" />
          </marker>
        </defs>
        {/* rotation label */}
        <text x="160" y="148" textAnchor="middle" fontSize="8" className="fill-slate-500">Clockwise</text>
        <text x="160" y="157" textAnchor="middle" fontSize="8" className="fill-slate-500">Rotation</text>
      </svg>
    </div>
  )
}

/* ---------- Sticky TOC with scroll-spy ---------- */
const TOC_ITEMS = [
  { id: 'philosophy', label: 'Core Philosophy' },
  { id: 'not-this', label: 'What This Is NOT' },
  { id: 'hierarchy', label: 'Three-Level Hierarchy' },
  { id: 'alignment', label: 'Multi-Level Alignment' },
  { id: 'pipeline', label: 'RS Engine Pipeline' },
  { id: 'rrg', label: 'RRG Explainer' },
  { id: 'reading', label: 'Reading the Charts' },
  { id: 'signals', label: 'Opportunity Signals' },
  { id: 'regime', label: 'Global Risk Regime' },
  { id: 'coverage', label: 'Market Coverage' },
]

export function StickyTOC(): JSX.Element {
  const [active, setActive] = useState('philosophy')

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting)
        if (visible.length > 0) {
          setActive(visible[0].target.id)
        }
      },
      { rootMargin: '-80px 0px -60% 0px', threshold: 0.1 },
    )
    TOC_ITEMS.forEach((item) => {
      const el = document.getElementById(item.id)
      if (el) observer.observe(el)
    })
    return () => observer.disconnect()
  }, [])

  return (
    <nav className="hidden xl:block">
      <div className="sticky top-24 space-y-1">
        <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-slate-400">On this page</p>
        {TOC_ITEMS.map((item) => (
          <a
            key={item.id}
            href={`#${item.id}`}
            className={`block rounded-md px-2.5 py-1 text-xs transition-colors ${
              active === item.id
                ? 'bg-teal-50 font-semibold text-teal-700'
                : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
            }`}
          >
            {item.label}
          </a>
        ))}
      </div>
    </nav>
  )
}

/* ---------- Shared data ---------- */
export const MARKET_COVERAGE = [
  { country: 'USA', index: 'S&P 500 / NASDAQ 100', source: 'Stooq', etf: 'SPY / QQQ' },
  { country: 'United Kingdom', index: 'FTSE 100', source: 'Stooq', etf: 'EWU' },
  { country: 'Germany', index: 'DAX 40', source: 'Stooq', etf: 'EWG' },
  { country: 'France', index: 'CAC 40', source: 'Stooq', etf: 'EWQ' },
  { country: 'Japan', index: 'Nikkei 225', source: 'Stooq', etf: 'EWJ' },
  { country: 'Hong Kong', index: 'Hang Seng', source: 'Stooq', etf: 'EWH' },
  { country: 'China', index: 'CSI 300', source: 'yfinance', etf: 'FXI / MCHI' },
  { country: 'South Korea', index: 'KOSPI', source: 'yfinance', etf: 'EWY' },
  { country: 'India', index: 'NIFTY 50', source: 'yfinance', etf: 'INDA' },
  { country: 'Taiwan', index: 'TWSE', source: 'yfinance', etf: 'EWT' },
  { country: 'Australia', index: 'ASX 200', source: 'yfinance', etf: 'EWA' },
  { country: 'Brazil', index: 'IBOVESPA', source: 'yfinance', etf: 'EWZ' },
  { country: 'Canada', index: 'TSX Composite', source: 'yfinance', etf: 'EWC' },
]
