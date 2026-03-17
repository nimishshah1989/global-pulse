import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from '@/components/layout/Layout'

const GlobalPulse = lazy(() => import('@/screens/GlobalPulse'))
const CountryDeepDive = lazy(() => import('@/screens/CountryDeepDive'))
const StockSelection = lazy(() => import('@/screens/StockSelection'))
const SectorMatrix = lazy(() => import('@/screens/SectorMatrix'))
const BasketBuilder = lazy(() => import('@/screens/BasketBuilder'))
const OpportunityScanner = lazy(() => import('@/screens/OpportunityScanner'))

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
      <Suspense fallback={<LoadingFallback />}>
        <Routes>
          <Route path="/" element={<Navigate to="/compass" replace />} />
          <Route path="/compass" element={<GlobalPulse />} />
          <Route path="/compass/country/:countryCode" element={<CountryDeepDive />} />
          <Route
            path="/compass/country/:countryCode/sector/:sectorSlug"
            element={<StockSelection />}
          />
          <Route path="/compass/matrix" element={<SectorMatrix />} />
          <Route path="/compass/baskets" element={<BasketBuilder />} />
          <Route path="/compass/baskets/:basketId" element={<BasketBuilder />} />
          <Route path="/compass/opportunities" element={<OpportunityScanner />} />
        </Routes>
      </Suspense>
    </Layout>
  )
}

export default App
