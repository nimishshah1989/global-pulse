import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from '@/components/layout/Layout'
import ErrorBoundary from '@/components/common/ErrorBoundary'

const GlobalPulse = lazy(() => import('@/screens/GlobalPulse'))
const CountryDeepDive = lazy(() => import('@/screens/CountryDeepDive'))
const StockSelection = lazy(() => import('@/screens/StockSelection'))
const SectorMatrix = lazy(() => import('@/screens/SectorMatrix'))
const BasketBuilder = lazy(() => import('@/screens/BasketBuilder'))
const TopETFs = lazy(() => import('@/screens/TopETFs'))
const OpportunityScanner = lazy(() => import('@/screens/OpportunityScanner'))
const Methodology = lazy(() => import('@/screens/Methodology'))

function LoadingFallback(): JSX.Element {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-slate-400 text-sm font-medium">Loading...</div>
    </div>
  )
}

function App(): JSX.Element {
  return (
    <Layout>
      <ErrorBoundary>
        <Suspense fallback={<LoadingFallback />}>
          <Routes>
            <Route path="/" element={<Navigate to="/compass" replace />} />
            <Route path="/compass" element={<GlobalPulse />} />
            <Route path="/compass/country/:countryCode" element={<CountryDeepDive />} />
            <Route path="/compass/country/:countryCode/sector/:sectorSlug" element={<StockSelection />} />
            <Route path="/compass/matrix" element={<SectorMatrix />} />
            <Route path="/compass/baskets" element={<BasketBuilder />} />
            <Route path="/compass/baskets/:basketId" element={<BasketBuilder />} />
            <Route path="/compass/etfs" element={<TopETFs />} />
            <Route path="/compass/opportunities" element={<OpportunityScanner />} />
            <Route path="/compass/methodology" element={<Methodology />} />
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </Layout>
  )
}

export default App
