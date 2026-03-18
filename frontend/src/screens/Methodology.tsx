import { useEffect, useState } from 'react'

const TOC = [
  { id: 'philosophy', label: 'Core Philosophy' },
  { id: 'not-this', label: 'What This Tool Is NOT' },
  { id: 'pipeline', label: 'RS Engine Pipeline' },
  { id: 'rrg', label: 'RRG Quadrant Rotation' },
  { id: 'hierarchy', label: 'Three-Level Hierarchy' },
  { id: 'alignment', label: 'Multi-Level Alignment' },
  { id: 'reading', label: 'Reading the Charts' },
  { id: 'signals', label: 'Opportunity Signals' },
  { id: 'coverage', label: 'Market Coverage' },
]

export default function Methodology(): JSX.Element {
  const [activeId, setActiveId] = useState('philosophy')

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.find((e) => e.isIntersecting)
        if (visible?.target.id) setActiveId(visible.target.id)
      },
      { rootMargin: '-20% 0px -60% 0px', threshold: 0.1 },
    )
    TOC.forEach(({ id }) => {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    })
    return () => observer.disconnect()
  }, [])

  return (
    <div className="mx-auto flex max-w-6xl gap-8">
      {/* Sticky TOC sidebar */}
      <nav className="hidden w-48 shrink-0 lg:block">
        <div className="sticky top-24 space-y-1">
          <p className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">On this page</p>
          {TOC.map(({ id, label }) => (
            <a key={id} href={`#${id}`}
              className={`block rounded-lg px-3 py-1.5 text-xs transition-colors ${activeId === id ? 'bg-teal-50 font-semibold text-teal-700' : 'text-slate-500 hover:text-slate-800'}`}
            >{label}</a>
          ))}
        </div>
      </nav>

      {/* Main content */}
      <div className="min-w-0 flex-1 space-y-8 pb-24">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Methodology & How It Works</h1>
          <p className="mt-1 text-sm text-slate-500">The complete Relative Strength engine behind Momentum Compass &mdash; every formula, every threshold, fully auditable.</p>
        </div>

        {/* Philosophy */}
        <Section id="philosophy" title="Core Philosophy">
          <p>Global liquidity flows like water &mdash; from weak markets to strong markets, from lagging sectors to leading sectors. <strong>Volume is the width of the river</strong>: it tells you how much capital is actually flowing.</p>
          <p className="mt-2">Relative Strength (RS) captures this flow numerically. An asset with rising RS and rising volume has institutional capital flowing in. An asset with falling RS and rising volume is being distributed. An asset with rising RS but falling volume is drifting up on thin air &mdash; it won&apos;t last.</p>
          <p className="mt-2">Every RS score, every ranking, every signal is traceable to a simple, auditable formula. No black boxes. No arbitrary thresholds that can&apos;t be explained.</p>
        </Section>

        {/* What This Tool Is NOT */}
        <Section id="not-this" title="What This Tool Is NOT">
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              { label: 'NOT fundamental analysis', desc: 'No earnings, PE ratios, or balance sheets. Price and volume are all that matter.' },
              { label: 'NOT a prediction model', desc: 'No machine learning, no forecasting. Pattern recognition and relative ranking only.' },
              { label: 'NOT a trading bot', desc: 'It surfaces opportunities and ranks them. Humans make all decisions.' },
              { label: 'NOT a backtesting engine', desc: 'It tracks forward-looking baskets, not curve-fitted optimized backtests.' },
            ].map((item) => (
              <div key={item.label} className="rounded-xl border border-red-100 bg-red-50/50 p-4">
                <h4 className="font-semibold text-red-800">{item.label}</h4>
                <p className="mt-1 text-xs text-red-700">{item.desc}</p>
              </div>
            ))}
          </div>
        </Section>

        {/* RS Engine Pipeline */}
        <Section id="pipeline" title="RS Engine Pipeline (10 Stages)">
          <div className="space-y-6">
            {PIPELINE_STAGES.map((s) => (
              <div key={s.stage} className="rounded-xl border border-slate-200 bg-slate-50/50 p-4">
                <h4 className="font-semibold text-slate-800">Stage {s.stage}: {s.title}</h4>
                <Code>{s.formula}</Code>
                <p className="mt-2 text-sm text-slate-600">{s.explanation}</p>
                <div className="mt-2 rounded-lg border border-teal-100 bg-teal-50/60 px-3 py-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-teal-600">Example</span>
                  <p className="mt-0.5 font-mono text-xs text-teal-800">{s.example}</p>
                </div>
                {s.extra}
              </div>
            ))}
          </div>
        </Section>

        {/* RRG Visual Explainer */}
        <Section id="rrg" title="RRG Quadrant Rotation">
          <p className="mb-4">Instruments rotate clockwise through four quadrants over time. The Relative Rotation Graph (RRG) plots RS Score on the X-axis and RS Momentum on the Y-axis.</p>
          <RRGDiagram />
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {QUADRANTS.map((q) => (
              <div key={q.name} className={`rounded-lg border px-3 py-2 ${q.color}`}>
                <span className="font-semibold">{q.name}</span>
                <p className="mt-0.5 text-xs opacity-80">{q.desc}</p>
                <p className="mt-1 text-[10px] font-medium opacity-60">Trading: {q.trading}</p>
              </div>
            ))}
          </div>
        </Section>

        {/* Hierarchy */}
        <Section id="hierarchy" title="Three-Level Hierarchy">
          <div className="grid gap-3 sm:grid-cols-3">
            <HierarchyCard level={1} title="Country" description="14 global market indices ranked against MSCI ACWI. Answers: Where is capital flowing?" color="bg-blue-50 border-blue-200" />
            <HierarchyCard level={2} title="Sector" description="Sector ETFs/indices within each country ranked against the country index. Answers: Which sectors are leading?" color="bg-teal-50 border-teal-200" />
            <HierarchyCard level={3} title="Stock" description="Individual stocks ranked against their sector benchmark. Answers: Which stocks are leading?" color="bg-purple-50 border-purple-200" />
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-2 text-left font-semibold text-slate-600">Level</th>
                <th className="px-4 py-2 text-left font-semibold text-slate-600">Asset Type</th>
                <th className="px-4 py-2 text-left font-semibold text-slate-600">Benchmark</th>
              </tr></thead>
              <tbody className="divide-y divide-slate-100">
                <tr><td className="px-4 py-2">1</td><td className="px-4 py-2">Country Index</td><td className="px-4 py-2">MSCI ACWI (ACWI ETF)</td></tr>
                <tr><td className="px-4 py-2">2</td><td className="px-4 py-2">Sector ETF/Index</td><td className="px-4 py-2">Country primary index</td></tr>
                <tr><td className="px-4 py-2">3</td><td className="px-4 py-2">Individual Stock</td><td className="px-4 py-2">Sector ETF/Index</td></tr>
                <tr><td className="px-4 py-2">Global</td><td className="px-4 py-2">Global Sector ETF</td><td className="px-4 py-2">MSCI ACWI</td></tr>
              </tbody>
            </table>
          </div>
        </Section>

        {/* Multi-Level Alignment */}
        <Section id="alignment" title="Multi-Level Alignment">
          <p className="mb-3">The highest-conviction signal occurs when all three hierarchy levels align in the same quadrant. Capital flows confirm at every level.</p>
          <div className="flex flex-col items-start gap-0">
            {[
              { emoji: '\uD83C\uDF0D', label: 'India', detail: 'LEADING globally', rs: 72, bg: 'bg-blue-50 border-blue-200' },
              { emoji: '\uD83D\uDCCA', label: 'NIFTY IT', detail: 'LEADING within India', rs: 78, bg: 'bg-teal-50 border-teal-200' },
              { emoji: '\uD83D\uDD0D', label: 'TCS', detail: 'LEADING within NIFTY IT', rs: 85, bg: 'bg-purple-50 border-purple-200' },
            ].map((item, i) => (
              <div key={item.label} className="flex items-center gap-3">
                {i > 0 && <div className="ml-6 h-4 w-px bg-slate-300" />}
                <div className={`flex items-center gap-2 rounded-lg border px-4 py-2 ${item.bg} ${i > 0 ? 'ml-' + (i * 4) : ''}`}>
                  <span className="text-lg">{item.emoji}</span>
                  <div>
                    <span className="font-semibold text-slate-800">{item.label}</span>
                    <span className="ml-2 text-xs text-slate-500">{item.detail}</span>
                    <span className="ml-2 rounded bg-emerald-100 px-1.5 py-0.5 font-mono text-[10px] font-bold text-emerald-700">RS: {item.rs}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-slate-500">When country + sector + stock are all in LEADING, the trade has the wind at its back at every level. This is the highest-conviction output of the system.</p>
        </Section>

        {/* Reading the Charts */}
        <Section id="reading" title="Reading the Charts">
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4">
              <h4 className="font-semibold text-slate-800">RS Line Chart</h4>
              <p className="mt-1 text-sm text-slate-600">The <span className="font-semibold text-blue-600">blue line</span> is the RS ratio; the <span className="font-semibold text-amber-600">orange line</span> is the 150-day moving average. Blue above orange = <span className="font-semibold text-emerald-600">outperforming</span>. Blue below orange = <span className="font-semibold text-red-600">underperforming</span>. Crossovers are regime change signals.</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4">
              <h4 className="font-semibold text-slate-800">RRG Scatter Plot</h4>
              <p className="mt-1 text-sm text-slate-600">Dots move clockwise: Improving (bottom-left) to Leading (top-right) to Weakening (bottom-right) to Lagging (bottom-left). Trailing tails show 4&ndash;8 weeks of trajectory. Dots moving toward the top-right corner are gaining both absolute strength and momentum.</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4">
              <h4 className="font-semibold text-slate-800">Heatmap Matrix</h4>
              <p className="mt-1 text-sm text-slate-600">Rows = sectors, columns = countries. Each cell shows the Adjusted RS Score colored from red (weak) to green (strong). Look for entire rows that are green (globally strong sector) or entire columns that are green (broadly strong country). Bright green cells where both the row and column headers are also strong represent the best opportunities.</p>
            </div>
          </div>
        </Section>

        {/* Signals */}
        <Section id="signals" title="Opportunity Signals">
          <div className="grid gap-3 sm:grid-cols-2">
            {SIGNALS.map((s) => (
              <SignalCard key={s.name} name={s.name} description={s.description} conviction={s.conviction} />
            ))}
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
              <h4 className="font-semibold text-emerald-800">RISK ON</h4>
              <p className="mt-1 text-sm text-emerald-700">ACWI above 200-day MA. Normal operation &mdash; surface momentum leaders, buy into strength.</p>
            </div>
            <div className="rounded-xl border border-red-200 bg-red-50 p-4">
              <h4 className="font-semibold text-red-800">RISK OFF</h4>
              <p className="mt-1 text-sm text-red-700">ACWI below 200-day MA. All signals get a warning flag. Shift to &ldquo;identify survivors&rdquo; and defensive sectors.</p>
            </div>
          </div>
        </Section>

        {/* Coverage */}
        <Section id="coverage" title="Market Coverage &amp; Data Sources">
          <div className="mb-4 grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <h4 className="font-semibold text-slate-800">Stooq (Primary)</h4>
              <p className="mt-1 text-sm text-slate-600">US, UK, Japan, Hong Kong stocks &amp; ETFs (~25,000 instruments). Global indices, currencies, bonds, commodities. Bulk CSV download + daily refresh at 02:00 UTC.</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <h4 className="font-semibold text-slate-800">yfinance (Gap-fill)</h4>
              <p className="mt-1 text-sm text-slate-600">India, South Korea, China A-shares, Taiwan, Australia, Brazil, Canada. Daily refresh after each market&apos;s close.</p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-2 text-left font-semibold text-slate-600">Market</th>
                <th className="px-4 py-2 text-left font-semibold text-slate-600">Index</th>
                <th className="px-4 py-2 text-left font-semibold text-slate-600">Source</th>
                <th className="px-4 py-2 text-left font-semibold text-slate-600">Country ETF</th>
              </tr></thead>
              <tbody className="divide-y divide-slate-100">
                {MARKET_COVERAGE.map((m) => (
                  <tr key={m.country}><td className="px-4 py-2 font-medium">{m.country}</td><td className="px-4 py-2 font-mono text-xs">{m.index}</td><td className="px-4 py-2">{m.source}</td><td className="px-4 py-2 font-mono text-xs">{m.etf}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      </div>
    </div>
  )
}

/* ---------- Helper components ---------- */

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }): JSX.Element {
  return (
    <section id={id} className="scroll-mt-24 rounded-xl border border-slate-200 bg-white p-6">
      <h2 className="mb-4 text-lg font-bold text-slate-900">{title}</h2>
      <div className="text-sm leading-relaxed text-slate-700">{children}</div>
    </section>
  )
}

function Code({ children }: { children: React.ReactNode }): JSX.Element {
  return <code className="mt-1 block rounded-lg bg-slate-100 px-3 py-2 font-mono text-xs text-slate-800">{children}</code>
}

function HierarchyCard({ level, title, description, color }: { level: number; title: string; description: string; color: string }): JSX.Element {
  return (
    <div className={`rounded-xl border p-4 ${color}`}>
      <div className="mb-1 text-xs font-bold uppercase tracking-wider text-slate-500">Level {level}</div>
      <h4 className="font-semibold text-slate-800">{title}</h4>
      <p className="mt-1 text-xs text-slate-600">{description}</p>
    </div>
  )
}

function SignalCard({ name, description, conviction }: { name: string; description: string; conviction: string }): JSX.Element {
  const colors: Record<string, string> = { 'Very High': 'bg-emerald-100 text-emerald-800', High: 'bg-emerald-50 text-emerald-700', Medium: 'bg-amber-50 text-amber-700', Caution: 'bg-red-50 text-red-700', Critical: 'bg-red-100 text-red-800' }
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between">
        <h4 className="font-semibold text-slate-800">{name}</h4>
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${colors[conviction] ?? 'bg-slate-100 text-slate-600'}`}>{conviction}</span>
      </div>
      <p className="mt-1 text-xs text-slate-600">{description}</p>
    </div>
  )
}

function RRGDiagram(): JSX.Element {
  return (
    <svg viewBox="0 0 320 240" className="mx-auto w-full max-w-md rounded-xl border border-slate-200 bg-white" role="img" aria-label="RRG Quadrant diagram showing clockwise rotation">
      {/* Grid lines */}
      <line x1="160" y1="10" x2="160" y2="230" stroke="#e2e8f0" strokeWidth="1" strokeDasharray="4" />
      <line x1="10" y1="120" x2="310" y2="120" stroke="#e2e8f0" strokeWidth="1" strokeDasharray="4" />
      {/* Axis labels */}
      <text x="160" y="238" textAnchor="middle" className="fill-slate-400" fontSize="9" fontFamily="Inter">RS Score &rarr;</text>
      <text x="6" y="120" textAnchor="middle" className="fill-slate-400" fontSize="9" fontFamily="Inter" transform="rotate(-90,6,120)">RS Momentum &rarr;</text>
      {/* Quadrant backgrounds */}
      <rect x="160" y="10" width="150" height="110" fill="#d1fae5" opacity="0.3" rx="4" />
      <rect x="160" y="120" width="150" height="110" fill="#fef3c7" opacity="0.3" rx="4" />
      <rect x="10" y="120" width="150" height="110" fill="#fee2e2" opacity="0.3" rx="4" />
      <rect x="10" y="10" width="150" height="110" fill="#dbeafe" opacity="0.3" rx="4" />
      {/* Quadrant names */}
      <text x="235" y="55" textAnchor="middle" fontSize="13" fontWeight="700" className="fill-emerald-700">LEADING</text>
      <text x="235" y="70" textAnchor="middle" fontSize="8" className="fill-emerald-600">RS &gt; 50, Mom &gt; 0</text>
      <text x="235" y="165" textAnchor="middle" fontSize="13" fontWeight="700" className="fill-amber-700">WEAKENING</text>
      <text x="235" y="180" textAnchor="middle" fontSize="8" className="fill-amber-600">RS &gt; 50, Mom &le; 0</text>
      <text x="85" y="165" textAnchor="middle" fontSize="13" fontWeight="700" className="fill-red-700">LAGGING</text>
      <text x="85" y="180" textAnchor="middle" fontSize="8" className="fill-red-600">RS &le; 50, Mom &le; 0</text>
      <text x="85" y="55" textAnchor="middle" fontSize="13" fontWeight="700" className="fill-blue-700">IMPROVING</text>
      <text x="85" y="70" textAnchor="middle" fontSize="8" className="fill-blue-600">RS &le; 50, Mom &gt; 0</text>
      {/* Clockwise rotation arrows */}
      <defs><marker id="arr" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="#64748b" /></marker></defs>
      <path d="M180,40 Q270,30 270,100" fill="none" stroke="#64748b" strokeWidth="1.5" markerEnd="url(#arr)" opacity="0.6" />
      <path d="M270,140 Q270,210 180,210" fill="none" stroke="#64748b" strokeWidth="1.5" markerEnd="url(#arr)" opacity="0.6" />
      <path d="M140,210 Q50,210 50,140" fill="none" stroke="#64748b" strokeWidth="1.5" markerEnd="url(#arr)" opacity="0.6" />
      <path d="M50,100 Q50,30 140,35" fill="none" stroke="#64748b" strokeWidth="1.5" markerEnd="url(#arr)" opacity="0.6" />
      {/* Center labels */}
      <text x="160" y="15" textAnchor="middle" fontSize="7" className="fill-slate-400">50</text>
      <text x="310" y="117" textAnchor="end" fontSize="7" className="fill-slate-400">0</text>
    </svg>
  )
}

/* ---------- Data ---------- */

const QUADRANTS = [
  { name: 'Leading', color: 'bg-emerald-100 text-emerald-800 border-emerald-200', desc: 'RS > 50, Momentum > 0 -- Strong and getting stronger', trading: 'Hold or add to winners. Highest-conviction positions.' },
  { name: 'Weakening', color: 'bg-amber-100 text-amber-800 border-amber-200', desc: 'RS > 50, Momentum <= 0 -- Strong but losing steam', trading: 'Tighten stops. Prepare to rotate out if momentum keeps falling.' },
  { name: 'Lagging', color: 'bg-red-100 text-red-800 border-red-200', desc: 'RS <= 50, Momentum <= 0 -- Weak and getting weaker', trading: 'Avoid. Capital is flowing out. No bottom-fishing.' },
  { name: 'Improving', color: 'bg-blue-100 text-blue-800 border-blue-200', desc: 'RS <= 50, Momentum > 0 -- Weak but turning around', trading: 'Early-stage watchlist. Wait for entry into Leading to confirm.' },
]

const WEIGHT_BAR = (
  <div className="mt-2 flex h-5 overflow-hidden rounded-full text-[10px] font-bold">
    <div className="flex items-center justify-center bg-teal-200 text-teal-800" style={{ width: '10%' }}>10%</div>
    <div className="flex items-center justify-center bg-teal-300 text-teal-900" style={{ width: '25%' }}>25%</div>
    <div className="flex items-center justify-center bg-teal-500 text-white" style={{ width: '35%' }}>35%</div>
    <div className="flex items-center justify-center bg-teal-400 text-teal-900" style={{ width: '30%' }}>30%</div>
  </div>
)

const VOL_CURVE = (
  <div className="mt-2 flex items-end gap-1">
    {[
      { ratio: '< 0.5', mult: '0.85', h: 'h-6', bg: 'bg-red-300' },
      { ratio: '0.5-1.0', mult: '1.00', h: 'h-8', bg: 'bg-slate-300' },
      { ratio: '1.0-1.5', mult: '1.00-1.15', h: 'h-10', bg: 'bg-emerald-300' },
      { ratio: '> 1.5', mult: '1.15', h: 'h-12', bg: 'bg-emerald-500' },
    ].map((b) => (
      <div key={b.ratio} className="flex flex-1 flex-col items-center">
        <span className="font-mono text-[10px] text-slate-600">{b.mult}</span>
        <div className={`w-full rounded-t ${b.h} ${b.bg}`} />
        <span className="mt-1 text-[9px] text-slate-500">{b.ratio}</span>
      </div>
    ))}
    <span className="ml-1 self-end text-[9px] text-slate-400">Vol Ratio</span>
  </div>
)

const PIPELINE_STAGES = [
  { stage: 1, title: 'RS Ratio (Raw RS Line)', formula: 'RS_Line[t] = (Close_asset[t] / Close_benchmark[t]) \u00D7 100', explanation: 'Normalized to 100 at the start of the lookback window. When it rises, the asset outperforms its benchmark; when it falls, it underperforms.', example: 'Apple: RS_Line = ($182.50 / $5,243) \u00D7 100 = 3.48 \u2014 if this rises from yesterday\'s 3.41, Apple is outperforming the S&P 500.' },
  { stage: 2, title: 'RS Trend (Mansfield RS)', formula: 'RS_MA[t] = SMA(RS_Line, 150 trading days)', explanation: 'RS_Line above its 150-day SMA = OUTPERFORMING. Below = UNDERPERFORMING. The 150-day window (~30 weeks) follows the Stan Weinstein / Mansfield standard \u2014 slow enough to filter noise, fast enough to catch regime changes within 1\u20132 months.', example: 'If RS_Line = 3.48 and RS_MA_150 = 3.32, then RS_Line > RS_MA \u2192 OUTPERFORMING.' },
  { stage: 3, title: 'Percentile Rank', formula: 'Excess_Return_nM = Asset_Return_nM \u2212 Benchmark_Return_nM\nRS_Percentile_nM = percentile_rank(Excess_Return_nM, within=peer_group)', explanation: 'For each timeframe (1M, 3M, 6M, 12M), compute excess return vs benchmark, then rank within the peer group on a 0\u2013100 percentile scale. We use percentile rank (NOT z-scores) because RS ratios violate normal distribution assumptions.', example: 'Apple 6M return: +18%. S&P 500 6M return: +12%. Excess: +6%. If 82 out of 100 peers had lower excess return \u2192 RS_Percentile_6M = 82.' },
  { stage: 4, title: 'Multi-Timeframe Composite', formula: 'RS_Composite = 1M \u00D7 0.10 + 3M \u00D7 0.25 + 6M \u00D7 0.35 + 12M \u00D7 0.30', explanation: 'The 6-month window gets the heaviest weight (35%) as the primary momentum window. Result: a 0\u2013100 score where higher = stronger relative performer across all timeframes.', example: '1M=70, 3M=75, 6M=82, 12M=68 \u2192 (70\u00D70.10)+(75\u00D70.25)+(82\u00D70.35)+(68\u00D70.30) = 7.0+18.75+28.7+20.4 = 74.85', extra: <div className="mt-2"><span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Weight distribution: 1M | 3M | 6M | 12M</span>{WEIGHT_BAR}</div> },
  { stage: 5, title: 'RS Momentum (Rate of Change)', formula: 'RS_Momentum = RS_Composite[today] \u2212 RS_Composite[20 trading days ago]\nRS_Momentum_Normalized = clip(RS_Momentum, \u221250, +50)', explanation: 'Positive = RS is improving (gaining strength vs peers). Negative = RS is deteriorating. Normalized to \u221250 to +50 for consistent plotting on the RRG Y-axis.', example: 'RS_Composite today = 74.85, 20 days ago = 69.20 \u2192 Momentum = +5.65 (improving).' },
  { stage: 6, title: 'Volume Conviction Adjustment', formula: 'Volume_Ratio = SMA(Volume, 20) / SMA(Volume, 100)\nAdjusted_RS_Score = RS_Composite \u00D7 vol_multiplier', explanation: 'Volume_Ratio > 1.0 means recent participation exceeds the long-term average (conviction). The multiplier is conservative: 0.85x to 1.15x. High volume confirms the signal; thin volume discounts it.', example: 'SMA_20_Vol = 12M shares, SMA_100_Vol = 8M shares \u2192 Vol_Ratio = 1.5 \u2192 multiplier = 1.15 \u2192 Adjusted = 74.85 \u00D7 1.15 = 86.08', extra: <div className="mt-2"><span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Multiplier curve by volume ratio</span>{VOL_CURVE}</div> },
  { stage: 7, title: 'Quadrant Classification (RRG)', formula: 'LEADING    = Adjusted_RS > 50 AND Momentum > 0\nWEAKENING  = Adjusted_RS > 50 AND Momentum \u2264 0\nLAGGING    = Adjusted_RS \u2264 50 AND Momentum \u2264 0\nIMPROVING  = Adjusted_RS \u2264 50 AND Momentum > 0', explanation: 'Each instrument is plotted on a 2D plane: X = Adjusted RS Score (0\u2013100, centered at 50), Y = RS Momentum (\u221250 to +50, centered at 0). Four quadrants define the rotation cycle.', example: 'Apple: Adjusted_RS = 86.08 (> 50), Momentum = +5.65 (> 0) \u2192 LEADING quadrant.' },
  { stage: 8, title: 'Liquidity Tier Assignment', formula: 'avg_daily_value = SMA(Close \u00D7 Volume, 20)\nTier 1: \u2265 $5M daily  |  Tier 2: $500K\u2013$5M  |  Tier 3: < $500K', explanation: 'Tier 1 = full confidence in all signals including volume. Tier 2 = volume as supporting evidence only. Tier 3 = volume signals unreliable, RS score capped at 70 regardless of raw score. Non-USD instruments are converted to USD equivalent.', example: 'Stock with avg daily value = $320K \u2192 Tier 3 \u2192 even if raw Adjusted_RS = 86, it gets capped to 70.' },
  { stage: 9, title: 'Regime Filter (Global Risk Overlay)', formula: 'RISK_ON  = ACWI_Close > SMA(ACWI_Close, 200)\nRISK_OFF = ACWI_Close < SMA(ACWI_Close, 200)', explanation: 'When ACWI is below its 200-day MA, the global environment is hostile. All opportunity signals get a warning flag. Recommendations shift from "buy leaders" to "identify survivors" and favor defensive sectors (Utilities, Staples, Healthcare).', example: 'ACWI = $104.20, 200-day MA = $106.50 \u2192 ACWI < MA \u2192 RISK_OFF. All signals flagged with caution.' },
  { stage: 10, title: 'Extension Warning', formula: 'extension_warning = (RS_Pct_3M > 95) AND (RS_Pct_6M > 95) AND (RS_Pct_12M > 90)', explanation: 'When an asset sits in the top 5% across all timeframes, it is "extended." This is NOT a sell signal \u2014 it is a risk management nudge. Extended assets can keep running, but the odds of mean reversion increase. Position sizing should reflect this.', example: 'Stock with 3M=97, 6M=98, 12M=93 \u2192 all thresholds met \u2192 extension_warning = true. Badge shown in UI.' },
]

const SIGNALS = [
  { name: 'Quadrant Entry: Leading', description: 'Instrument just crossed into the Leading quadrant (high RS + rising momentum).', conviction: 'High' },
  { name: 'Quadrant Entry: Improving', description: 'Entered Improving quadrant (low RS but momentum turning positive) \u2014 early-stage signal.', conviction: 'Medium' },
  { name: 'Volume Breakout', description: 'RS turning positive + volume > 1.5x average. Institutional participation confirmed.', conviction: 'High' },
  { name: 'Multi-Level Alignment', description: 'Country + Sector + Stock all in Leading quadrant simultaneously. Highest conviction.', conviction: 'Very High' },
  { name: 'Extension Alert', description: 'RS in top 5% across all timeframes. Not a sell signal \u2014 a risk management nudge.', conviction: 'Caution' },
  { name: 'Regime Change', description: 'ACWI crossed above/below its 200-day MA. Global risk regime shifted.', conviction: 'Critical' },
]

const MARKET_COVERAGE = [
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
