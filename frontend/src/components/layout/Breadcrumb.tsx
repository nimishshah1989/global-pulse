import { Link, useLocation } from 'react-router-dom'

const COUNTRY_NAMES: Record<string, string> = {
  US: 'United States',
  UK: 'United Kingdom',
  JP: 'Japan',
  HK: 'Hong Kong',
  CN: 'China',
  KR: 'South Korea',
  IN: 'India',
  TW: 'Taiwan',
  AU: 'Australia',
  BR: 'Brazil',
  CA: 'Canada',
  DE: 'Germany',
  FR: 'France',
}

function formatSectorName(slug: string): string {
  return slug
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export default function Breadcrumb(): JSX.Element {
  const location = useLocation()
  const segments = location.pathname.split('/').filter(Boolean)

  const crumbs: { label: string; to: string }[] = [{ label: 'Global', to: '/compass' }]

  if (segments.length >= 3 && segments[1] === 'country') {
    const countryCode = segments[2]
    crumbs.push({
      label: COUNTRY_NAMES[countryCode] ?? countryCode,
      to: `/compass/country/${countryCode}`,
    })

    if (segments.length >= 5 && segments[3] === 'sector') {
      const sectorSlug = segments[4]
      crumbs.push({
        label: formatSectorName(sectorSlug),
        to: `/compass/country/${countryCode}/sector/${sectorSlug}`,
      })
    }
  }

  if (crumbs.length <= 1) {
    return <div />
  }

  return (
    <nav className="flex items-center gap-2 text-sm text-slate-500">
      {crumbs.map((crumb, index) => (
        <span key={crumb.to} className="flex items-center gap-2">
          {index > 0 && <span className="text-slate-300">/</span>}
          {index === crumbs.length - 1 ? (
            <span className="font-medium text-slate-900">{crumb.label}</span>
          ) : (
            <Link to={crumb.to} className="hover:text-primary-600 transition-colors">
              {crumb.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  )
}
