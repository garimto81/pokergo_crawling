import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient()

// Pages (placeholder)
function Dashboard() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
      <p className="text-gray-600">Sheet to Sheet Migration 대시보드</p>
    </div>
  )
}

function Migration() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Migration</h1>
      <p className="text-gray-600">마이그레이션 설정 및 실행</p>
    </div>
  )
}

function Scheduler() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Scheduler</h1>
      <p className="text-gray-600">트리거 및 스케줄 관리</p>
    </div>
  )
}

function History() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">History</h1>
      <p className="text-gray-600">실행 이력</p>
    </div>
  )
}

// Layout
function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <span className="text-xl font-bold text-blue-600">Sheet2Sheet</span>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                <Link to="/" className="border-transparent text-gray-500 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                  Dashboard
                </Link>
                <Link to="/migration" className="border-transparent text-gray-500 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                  Migration
                </Link>
                <Link to="/scheduler" className="border-transparent text-gray-500 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                  Scheduler
                </Link>
                <Link to="/history" className="border-transparent text-gray-500 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                  History
                </Link>
              </div>
            </div>
          </div>
        </div>
      </nav>
      <main>{children}</main>
    </div>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/migration" element={<Migration />} />
            <Route path="/scheduler" element={<Scheduler />} />
            <Route path="/history" element={<History />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
