export default function Methodology(): JSX.Element {
  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          Methodology & How It Works
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Understanding the Relative Strength engine behind Momentum Compass
        </p>
      </div>

      {/* Philosophy */}
      <Section title="Core Philosophy">
        <p>
          Global liquidity flows like water &mdash; from weak markets to strong
          markets, from lagging sectors to leading sectors, from underperformers
          to outperformers. <strong>Volume is the width of the river</strong>: it
          tells you how much capital is actually flowing.
        </p>
        <p className="mt-2">
          Relative Strength (RS) captures this flow numerically. An asset with
          rising RS and rising volume has institutional capital flowing in. An
          asset with falling RS and rising volume is being distributed. An asset
          with rising RS but falling volume is drifting up on thin air &mdash; it
          won&apos;t last.
        </p>
      </Section>

      {/* RS Engine Pipeline */}
      <Section title="The RS Engine Pipeline">
        <ol className="list-decimal space-y-4 pl-5">
          <li>
            <h4 className="font-semibold text-slate-800">RS Ratio (Raw RS Line)</h4>
            <Code>RS_Line = (Close_asset / Close_benchmark) &times; 100</Code>
            <p className="mt-1 text-sm text-slate-600">
              Normalized to 100 at the start of the lookback window. When it
              rises, the asset outperforms its benchmark; when it falls, the
              asset underperforms.
            </p>
          </li>

          <li>
            <h4 className="font-semibold text-slate-800">RS Trend (Mansfield RS)</h4>
            <Code>RS_MA = SMA(RS_Line, 150 days)</Code>
            <p className="mt-1 text-sm text-slate-600">
              If RS_Line &gt; RS_MA the asset is{' '}
              <span className="font-semibold text-emerald-600">OUTPERFORMING</span>;
              otherwise{' '}
              <span className="font-semibold text-red-600">UNDERPERFORMING</span>.
              The 150-day SMA (~30 weeks) follows the Stan Weinstein / Mansfield
              standard.
            </p>
          </li>

          <li>
            <h4 className="font-semibold text-slate-800">Percentile Rank</h4>
            <p className="text-sm text-slate-600">
              For each timeframe (1M, 3M, 6M, 12M), compute excess return over
              benchmark, then rank within the peer group on a 0&ndash;100
              percentile scale. We use percentile rank (not z-scores) because RS
              ratios don&apos;t follow a normal distribution.
            </p>
          </li>

          <li>
            <h4 className="font-semibold text-slate-800">Multi-Timeframe Composite</h4>
            <Code>
              Composite = 1M &times; 0.10 + 3M &times; 0.25 + 6M &times; 0.35 + 12M &times; 0.30
            </Code>
            <p className="mt-1 text-sm text-slate-600">
              6-month window gets the heaviest weight &mdash; it&apos;s the
              primary momentum window. Result: a 0&ndash;100 score where higher
              = stronger relative performer.
            </p>
          </li>

          <li>
            <h4 className="font-semibold text-slate-800">RS Momentum (Rate of Change)</h4>
            <Code>RS_Momentum = Composite[today] &minus; Composite[20 days ago]</Code>
            <p className="mt-1 text-sm text-slate-600">
              Positive = RS improving (gaining strength vs peers). Negative = RS
              deteriorating. Normalized to &minus;50 to +50.
            </p>
          </li>

          <li>
            <h4 className="font-semibold text-slate-800">Volume Conviction</h4>
            <Code>Volume_Ratio = SMA(Volume, 20) / SMA(Volume, 100)</Code>
            <p className="mt-1 text-sm text-slate-600">
              Adjusts the composite score by &plusmn;15% based on volume
              conviction. High recent volume = more confidence in the signal.
              Low volume = discount the signal. Illiquid instruments (Tier 3) are
              capped at score 70.
            </p>
          </li>

          <li>
            <h4 className="font-semibold text-slate-800">Quadrant Classification (RRG)</h4>
            <QuadrantExplainer />
          </li>
        </ol>
      </Section>

      {/* Hierarchy */}
      <Section title="Three-Level Hierarchy">
        <div className="grid gap-3 sm:grid-cols-3">
          <HierarchyCard
            level={1}
            title="Country"
            description="14 global market indices ranked against MSCI ACWI. Answers: Where is capital flowing?"
            color="bg-blue-50 border-blue-200"
          />
          <HierarchyCard
            level={2}
            title="Sector"
            description="Sector ETFs/indices within each country ranked against the country index. Answers: Which sectors are leading?"
            color="bg-teal-50 border-teal-200"
          />
          <HierarchyCard
            level={3}
            title="Stock"
            description="Individual stocks ranked against their sector benchmark. Answers: Which stocks are leading?"
            color="bg-purple-50 border-purple-200"
          />
        </div>
      </Section>

      {/* Benchmarks */}
      <Section title="Benchmark Assignments">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-2 text-left font-semibold text-slate-600">Level</th>
                <th className="px-4 py-2 text-left font-semibold text-slate-600">Asset Type</th>
                <th className="px-4 py-2 text-left font-semibold text-slate-600">Benchmark</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <tr><td className="px-4 py-2">1</td><td className="px-4 py-2">Country Index</td><td className="px-4 py-2">MSCI ACWI (ACWI ETF)</td></tr>
              <tr><td className="px-4 py-2">2</td><td className="px-4 py-2">Sector ETF/Index</td><td className="px-4 py-2">Country primary index</td></tr>
              <tr><td className="px-4 py-2">3</td><td className="px-4 py-2">Individual Stock</td><td className="px-4 py-2">Sector ETF/Index</td></tr>
              <tr><td className="px-4 py-2">Global</td><td className="px-4 py-2">Global Sector ETF</td><td className="px-4 py-2">MSCI ACWI</td></tr>
            </tbody>
          </table>
        </div>
      </Section>

      {/* Signals */}
      <Section title="Opportunity Signals">
        <div className="grid gap-3 sm:grid-cols-2">
          <SignalCard
            name="Quadrant Entry: Leading"
            description="Instrument just crossed into the Leading quadrant (high RS + rising momentum)"
            conviction="High"
          />
          <SignalCard
            name="Quadrant Entry: Improving"
            description="Instrument entered the Improving quadrant (low RS but momentum turning positive) - early signal"
            conviction="Medium"
          />
          <SignalCard
            name="Volume Breakout"
            description="RS turning positive combined with volume >1.5x average - institutional participation confirmed"
            conviction="High"
          />
          <SignalCard
            name="Multi-Level Alignment"
            description="Country + Sector + Stock all in Leading quadrant simultaneously - highest conviction signal"
            conviction="Very High"
          />
          <SignalCard
            name="Extension Alert"
            description="RS in top 5% across all timeframes - not a sell signal, a risk management nudge"
            conviction="Caution"
          />
          <SignalCard
            name="Regime Change"
            description="ACWI crossed above/below its 200-day moving average - global risk regime shifted"
            conviction="Critical"
          />
        </div>
      </Section>

      {/* Risk Regime */}
      <Section title="Global Risk Regime">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
            <h4 className="font-semibold text-emerald-800">RISK ON</h4>
            <p className="mt-1 text-sm text-emerald-700">
              ACWI is above its 200-day MA. Normal operation &mdash; surface
              momentum leaders, recommend buying into strength.
            </p>
          </div>
          <div className="rounded-xl border border-red-200 bg-red-50 p-4">
            <h4 className="font-semibold text-red-800">RISK OFF</h4>
            <p className="mt-1 text-sm text-red-700">
              ACWI is below its 200-day MA. All signals get a warning flag.
              Recommendations shift to &ldquo;identify survivors&rdquo; and
              favour defensive sectors.
            </p>
          </div>
        </div>
      </Section>

      {/* Liquidity Tiers */}
      <Section title="Liquidity Tiers">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-bold text-emerald-700">Tier 1</span>
              <span className="text-sm font-medium text-slate-700">&ge;$5M daily value</span>
            </div>
            <p className="mt-2 text-xs text-slate-500">Full confidence in all signals including volume.</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-bold text-amber-700">Tier 2</span>
              <span className="text-sm font-medium text-slate-700">$500K&ndash;$5M daily</span>
            </div>
            <p className="mt-2 text-xs text-slate-500">Volume as supporting evidence only.</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-bold text-red-700">Tier 3</span>
              <span className="text-sm font-medium text-slate-700">&lt;$500K daily</span>
            </div>
            <p className="mt-2 text-xs text-slate-500">Flagged. Volume signals unreliable. RS score capped at 70.</p>
          </div>
        </div>
      </Section>

      {/* Data Sources */}
      <Section title="Data Sources">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h4 className="font-semibold text-slate-800">Stooq (Primary)</h4>
            <p className="mt-1 text-sm text-slate-600">
              US, UK, Japan, Hong Kong stocks &amp; ETFs. Global indices,
              currencies, bonds, commodities. Bulk CSV download &amp; daily
              refresh.
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h4 className="font-semibold text-slate-800">yfinance (Gap-fill)</h4>
            <p className="mt-1 text-sm text-slate-600">
              India, South Korea, China A-shares, Taiwan, Australia, Brazil,
              Canada. Daily refresh after market close.
            </p>
          </div>
        </div>
      </Section>

      {/* Coverage */}
      <Section title="Market Coverage">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-2 text-left font-semibold text-slate-600">Market</th>
                <th className="px-4 py-2 text-left font-semibold text-slate-600">Index</th>
                <th className="px-4 py-2 text-left font-semibold text-slate-600">Source</th>
                <th className="px-4 py-2 text-left font-semibold text-slate-600">Country ETF</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {MARKET_COVERAGE.map((m) => (
                <tr key={m.country}>
                  <td className="px-4 py-2 font-medium">{m.country}</td>
                  <td className="px-4 py-2 font-mono text-xs">{m.index}</td>
                  <td className="px-4 py-2">{m.source}</td>
                  <td className="px-4 py-2 font-mono text-xs">{m.etf}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  )
}

/* ---------- Helper components ---------- */

function Section({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}): JSX.Element {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6">
      <h2 className="mb-4 text-lg font-bold text-slate-900">{title}</h2>
      <div className="text-sm leading-relaxed text-slate-700">{children}</div>
    </section>
  )
}

function Code({ children }: { children: React.ReactNode }): JSX.Element {
  return (
    <code className="mt-1 block rounded-lg bg-slate-100 px-3 py-2 font-mono text-xs text-slate-800">
      {children}
    </code>
  )
}

function QuadrantExplainer(): JSX.Element {
  const quadrants = [
    { name: 'Leading', color: 'bg-emerald-100 text-emerald-800 border-emerald-200', desc: 'RS > 50, Momentum > 0 — Strong and getting stronger' },
    { name: 'Weakening', color: 'bg-amber-100 text-amber-800 border-amber-200', desc: 'RS > 50, Momentum ≤ 0 — Strong but losing momentum' },
    { name: 'Lagging', color: 'bg-red-100 text-red-800 border-red-200', desc: 'RS ≤ 50, Momentum ≤ 0 — Weak and getting weaker' },
    { name: 'Improving', color: 'bg-blue-100 text-blue-800 border-blue-200', desc: 'RS ≤ 50, Momentum > 0 — Weak but momentum turning' },
  ]

  return (
    <div className="mt-2 grid gap-2 sm:grid-cols-2">
      {quadrants.map((q) => (
        <div key={q.name} className={`rounded-lg border px-3 py-2 ${q.color}`}>
          <span className="font-semibold">{q.name}</span>
          <p className="mt-0.5 text-xs opacity-80">{q.desc}</p>
        </div>
      ))}
    </div>
  )
}

function HierarchyCard({
  level,
  title,
  description,
  color,
}: {
  level: number
  title: string
  description: string
  color: string
}): JSX.Element {
  return (
    <div className={`rounded-xl border p-4 ${color}`}>
      <div className="mb-1 text-xs font-bold uppercase tracking-wider text-slate-500">
        Level {level}
      </div>
      <h4 className="font-semibold text-slate-800">{title}</h4>
      <p className="mt-1 text-xs text-slate-600">{description}</p>
    </div>
  )
}

function SignalCard({
  name,
  description,
  conviction,
}: {
  name: string
  description: string
  conviction: string
}): JSX.Element {
  const convictionColor: Record<string, string> = {
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
        <span
          className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${convictionColor[conviction] ?? 'bg-slate-100 text-slate-600'}`}
        >
          {conviction}
        </span>
      </div>
      <p className="mt-1 text-xs text-slate-600">{description}</p>
    </div>
  )
}

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
