export type ViewMode = 'kanban' | 'table'

interface ViewToggleProps {
  value: ViewMode
  onChange: (view: ViewMode) => void
}

export default function ViewToggle({ value, onChange }: ViewToggleProps): JSX.Element {
  return (
    <div className="flex items-center rounded-lg border border-slate-200 overflow-hidden">
      <button
        onClick={() => onChange('kanban')}
        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors ${
          value === 'kanban'
            ? 'bg-teal-600 text-white'
            : 'bg-white text-slate-500 hover:bg-slate-50'
        }`}
        title="Action Board view"
      >
        {/* Grid icon */}
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
        </svg>
        Board
      </button>
      <button
        onClick={() => onChange('table')}
        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors ${
          value === 'table'
            ? 'bg-teal-600 text-white'
            : 'bg-white text-slate-500 hover:bg-slate-50'
        }`}
        title="Table view"
      >
        {/* List icon */}
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
        </svg>
        Table
      </button>
    </div>
  )
}
