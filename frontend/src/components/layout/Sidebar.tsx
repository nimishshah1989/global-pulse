import { NavLink, useLocation } from 'react-router-dom'

interface NavItem {
  to: string
  icon: string
  label: string
}

const NAV_ITEMS: NavItem[] = [
  { to: '/compass', icon: '\uD83C\uDF0D', label: 'Global Pulse' },
  { to: '/compass/country/US', icon: '\uD83D\uDCCA', label: 'Country Deep Dive' },
  { to: '/compass/matrix', icon: '\uD83D\uDD00', label: 'Sector Matrix' },
  { to: '/compass/baskets', icon: '\uD83D\uDCE6', label: 'My Baskets' },
  { to: '/compass/opportunities', icon: '\uD83C\uDFAF', label: 'Opportunities' },
  { to: '/compass/methodology', icon: '\uD83D\uDCD6', label: 'Methodology' },
]

export default function Sidebar(): JSX.Element {
  const location = useLocation()
  return (
    <aside className="flex h-full w-64 flex-col border-r border-slate-200 bg-white">
      <div className="flex items-center gap-2 border-b border-slate-200 px-6 py-5">
        <span className="text-xl font-bold text-primary-600">Momentum Compass</span>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/compass'}
            className={({ isActive }) => {
              const active = isActive || (item.to === '/compass/country/US' && location.pathname.startsWith('/compass/country'))
              return `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                active
                  ? 'bg-primary-600 text-white'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`
            }}
          >
            <span className="text-base">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-slate-200 px-3 py-4" />
    </aside>
  )
}
