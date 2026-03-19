export default function Header(): JSX.Element {
  return (
    <header className="border-b border-slate-200 bg-white px-6 py-3">
      <div className="flex items-center justify-between">
        <div className="text-sm text-slate-500">Momentum Compass</div>
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
          Live data
        </div>
      </div>
    </header>
  )
}
