import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from '@/components/layout/Layout'
import ErrorBoundary from '@/components/common/ErrorBoundary'

const Countries = lazy(() => import('@/screens/Countries'))
const Sectors = lazy(() => import('@/screens/Sectors'))
const ETFs = lazy(() => import('@/screens/ETFs'))

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
            <Route path="/compass" element={<Countries />} />
            <Route path="/compass/country/:countryCode" element={<Sectors />} />
            <Route path="/compass/country/:countryCode/sector/:sectorSlug" element={<ETFs />} />
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </Layout>
  )
}

export default App
