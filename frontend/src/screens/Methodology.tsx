import { useEffect, useState } from 'react'

const TOC = [
  { id: 'philosophy', label: 'Core Philosophy' },
  { id: 'not-this', label: 'What This Tool Is NOT' },
  { id: 'indicators', label: 'Three Indicators' },
  { id: 'actions', label: 'Action Matrix (8 Actions)' },
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
          <p className="mt-1 text-sm text-slate-500">The v2 RS engine uses 3 indicators and an 8-action matrix &mdash; fully auditable, no black boxes.</p>
        </div>

        {/* Philosophy */}
        <Section id="philosophy" title="Core Philosophy">
          <p>Global liquidity flows like water &mdash; from weak markets to strong markets, from lagging sectors to leading sectors. <strong>Volume is the width of the river</strong>: it tells you how much capital is actually flowing.</p>
          <p className="mt-2">Relative Strength (RS) captures this flow numerically. The v2 engine distills everything into <strong>3 observable indicators</strong> and maps them to <strong>8 clear actions</strong>. Every recommendation is traceable to these indicators.</p>
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

        {/* Three Indicators */}
        <Section id="indicators" title="Three Indicators">
          <p className="mb-4">The v2 engine uses exactly 3 indicators. Each captures a different dimension of relative strength.</p>
          <div className="space-y-4">
            <IndicatorCard
              number={1}
              title="Price Trend (RS Line vs MA)"
              formula="RS_Line = (Close_asset / Close_benchmark) x 100"
              subFormula="RS_MA = SMA(RS_Line, 150 days)"
              output="OUTPERFORMING (RS above MA) or UNDERPERFORMING (RS below MA)"
              explanation="The RS Line divided by its 150-day moving average determines if the asset is in a structural uptrend or downtrend relative to its benchmark. This is the Mansfield Relative Strength approach."
              color="border-blue-200 bg-blue-50/50"
            />
            <IndicatorCard
              number={2}
              title="Momentum (RS Rate of Change)"
              formula="RS_Momentum_Pct = ((RS_Line[today] / RS_Line[20 days ago]) - 1) x 100"
              output="ACCELERATING (positive) or DECELERATING (negative)"
              explanation="Measures whether relative performance is improving or deteriorating over the last 20 trading days. Positive = gaining relative strength. Negative = losing relative strength."
              color="border-teal-200 bg-teal-50/50"
            />
            <IndicatorCard
              number={3}
              title="OBV (On-Balance Volume Character)"
              formula="OBV trend analysis: rising OBV = ACCUMULATION, falling OBV = DISTRIBUTION"
              output="ACCUMULATION, DISTRIBUTION, or NEUTRAL"
              explanation="On-Balance Volume reveals whether smart money is accumulating (buying into) or distributing (selling out of) the asset. Volume confirms or denies the price trend."
              color="border-purple-200 bg-purple-50/50"
            />
          </div>
        </Section>

        {/* Action Matrix */}
        <Section id="actions" title="Action Matrix (8 Actions)">
          <p className="mb-4">The 3 indicators combine into 8 possible actions. Each action has a clear definition based on which indicators are positive/negative.</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-3 py-2 text-left font-semibold text-slate-600">Action</th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-600">Price Trend</th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-600">Momentum</th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-600">OBV</th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-600">Meaning</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {ACTION_MATRIX.map((row) => (
                  <tr key={row.action} className={row.rowBg}>
                    <td className={`px-3 py-2 font-semibold ${row.actionColor}`}>{row.action}</td>
                    <td className="px-3 py-2 font-mono text-xs">{row.priceTrend}</td>
                    <td className="px-3 py-2 font-mono text-xs">{row.momentum}</td>
                    <td className="px-3 py-2 font-mono text-xs">{row.obv}</td>
                    <td className="px-3 py-2 text-xs text-slate-600">{row.meaning}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-slate-500">The weight recommendation (Overweight / Neutral / Reduce / Underweight / Watch / Accumulate / Avoid) maps directly from the action.</p>
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
          <p className="mb-3">The highest-conviction signal occurs when all three hierarchy levels show BUY action. Capital flows confirm at every level.</p>
          <div className="flex flex-col items-start gap-0">
            {[
              { label: 'India', detail: 'BUY globally', rs: 72, bg: 'bg-blue-50 border-blue-200' },
              { label: 'NIFTY IT', detail: 'BUY within India', rs: 78, bg: 'bg-teal-50 border-teal-200' },
              { label: 'TCS', detail: 'BUY within NIFTY IT', rs: 85, bg: 'bg-purple-50 border-purple-200' },
            ].map((item, i) => (
              <div key={item.label} className="flex items-center gap-3">
                {i > 0 && <div className="ml-6 h-4 w-px bg-slate-300" />}
                <div className={`flex items-center gap-2 rounded-lg border px-4 py-2 ${item.bg}`}>
                  <div>
                    <span className="font-semibold text-slate-800">{item.label}</span>
                    <span className="ml-2 text-xs text-slate-500">{item.detail}</span>
                    <span className="ml-2 rounded bg-emerald-100 px-1.5 py-0.5 font-mono text-[10px] font-bold text-emerald-700">RS: {item.rs}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-slate-500">When country + sector + stock are all BUY, the trade has the wind at its back at every level. This is the highest-conviction output of the system.</p>
        </Section>

        {/* Reading the Charts */}
        <Section id="reading" title="Reading the Charts">
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4">
              <h4 className="font-semibold text-slate-800">RS Line Chart</h4>
              <p className="mt-1 text-sm text-slate-600">The <span className="font-semibold text-blue-600">blue line</span> is the RS ratio; the <span className="font-semibold text-amber-600">orange line</span> is the 150-day moving average. Blue above orange = <span className="font-semibold text-emerald-600">OUTPERFORMING</span>. Blue below orange = <span className="font-semibold text-red-600">UNDERPERFORMING</span>. Crossovers are regime change signals.</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4">
              <h4 className="font-semibold text-slate-800">RRG Scatter Plot</h4>
              <p className="mt-1 text-sm text-slate-600">Dots are plotted on RS Score (X) vs RS Momentum (Y). Trailing tails show 4&ndash;8 weeks of trajectory. Dots in the top-right (high score + positive momentum) correspond to BUY actions. Bottom-left = SELL/AVOID territory.</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4">
              <h4 className="font-semibold text-slate-800">Heatmap Matrix</h4>
              <p className="mt-1 text-sm text-slate-600">Rows = sectors, columns = countries. Each cell shows the RS Score colored from red (weak) to green (strong). In Action View, cells display the recommended action (BUY, SELL, etc.) with corresponding colors.</p>
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
              <p className="mt-1 text-sm text-slate-600">US, UK, Japan, Hong Kong stocks &amp; ETFs (~25,000 instruments). Global indices, currencies, bonds, commodities.</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <h4 className="font-semibold text-slate-800">yfinance (Gap-fill)</h4>
              <p className="mt-1 text-sm text-slate-600">India, South Korea, China A-shares, Taiwan, Australia, Brazil, Canada.</p>
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

function IndicatorCard({ number, title, formula, subFormula, output, explanation, color }: {
  number: number; title: string; formula: string; subFormula?: string; output: string; explanation: string; color: string
}): JSX.Element {
  return (
    <div className={`rounded-xl border p-4 ${color}`}>
      <div className="mb-1 text-xs font-bold uppercase tracking-wider text-slate-500">Indicator {number}</div>
      <h4 className="font-semibold text-slate-800">{title}</h4>
      <code className="mt-1 block rounded-lg bg-slate-100 px-3 py-2 font-mono text-xs text-slate-800">{formula}</code>
      {subFormula && <code className="mt-1 block rounded-lg bg-slate-100 px-3 py-2 font-mono text-xs text-slate-800">{subFormula}</code>}
      <div className="mt-2 rounded-lg border border-teal-100 bg-teal-50/60 px-3 py-2">
        <span className="text-[10px] font-bold uppercase tracking-wider text-teal-600">Output</span>
        <p className="mt-0.5 font-mono text-xs text-teal-800">{output}</p>
      </div>
      <p className="mt-2 text-xs text-slate-600">{explanation}</p>
    </div>
  )
}

/* ---------- Data ---------- */

const ACTION_MATRIX = [
  { action: 'BUY', priceTrend: 'OUTPERFORMING', momentum: 'ACCELERATING', obv: 'ACCUMULATION', meaning: 'All 3 indicators aligned bullish. Strongest conviction.', actionColor: 'text-emerald-700', rowBg: 'bg-emerald-50/30' },
  { action: 'HOLD (Divergence)', priceTrend: 'OUTPERFORMING', momentum: 'ACCELERATING', obv: 'DISTRIBUTION', meaning: 'Price strong but smart money distributing. Caution.', actionColor: 'text-yellow-700', rowBg: '' },
  { action: 'HOLD (Fading)', priceTrend: 'OUTPERFORMING', momentum: 'DECELERATING', obv: 'ACCUMULATION', meaning: 'Still outperforming but momentum fading. Watch closely.', actionColor: 'text-yellow-700', rowBg: '' },
  { action: 'REDUCE', priceTrend: 'OUTPERFORMING', momentum: 'DECELERATING', obv: 'DISTRIBUTION', meaning: 'Outperforming but fading with distribution. Trim positions.', actionColor: 'text-orange-700', rowBg: 'bg-orange-50/30' },
  { action: 'SELL', priceTrend: 'UNDERPERFORMING', momentum: 'DECELERATING', obv: 'DISTRIBUTION', meaning: 'All 3 indicators aligned bearish. Exit.', actionColor: 'text-red-700', rowBg: 'bg-red-50/30' },
  { action: 'WATCH', priceTrend: 'UNDERPERFORMING', momentum: 'DECELERATING', obv: 'ACCUMULATION', meaning: 'Weak but accumulation starting. Early watchlist.', actionColor: 'text-blue-700', rowBg: '' },
  { action: 'ACCUMULATE', priceTrend: 'UNDERPERFORMING', momentum: 'ACCELERATING', obv: 'ACCUMULATION', meaning: 'Momentum turning with accumulation. Build position.', actionColor: 'text-teal-700', rowBg: 'bg-teal-50/30' },
  { action: 'AVOID', priceTrend: 'UNDERPERFORMING', momentum: 'ACCELERATING', obv: 'DISTRIBUTION', meaning: 'Momentum turn but on distribution. False signal risk.', actionColor: 'text-slate-600', rowBg: '' },
]

const SIGNALS = [
  { name: 'Action: BUY', description: 'Instrument has all 3 indicators aligned bullish (outperforming + accelerating + accumulation).', conviction: 'High' },
  { name: 'Action: ACCUMULATE', description: 'Momentum turning positive with accumulation detected. Early entry signal.', conviction: 'Medium' },
  { name: 'Volume Breakout', description: 'RS turning positive + volume surge. Institutional participation confirmed.', conviction: 'High' },
  { name: 'Multi-Level Alignment', description: 'Country + Sector + Stock all showing BUY action simultaneously. Highest conviction.', conviction: 'Very High' },
  { name: 'Extension Alert', description: 'RS in top 5% across all timeframes. Not a sell signal -- a risk management nudge.', conviction: 'Caution' },
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
