import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Files,
  FolderTree,
  Settings,
  FileCode2,
  CheckSquare,
  Layers
} from 'lucide-react';

const navItems = [
  { path: '/', label: 'Explorer', icon: Layers },
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/files', label: 'Files', icon: Files },
  { path: '/groups', label: 'Groups', icon: FolderTree },
  { path: '/entries', label: 'Entries', icon: CheckSquare },
  { path: '/patterns', label: 'Patterns', icon: FileCode2 },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const isExplorerPage = location.pathname === '/' || location.pathname === '/explorer';

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <FolderTree className="w-8 h-8 text-blue-600" />
              <span className="text-xl font-bold text-gray-900">NAMS</span>
              <span className="text-sm text-gray-500">NAS Asset Management</span>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-4">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path ||
                (item.path === '/' && location.pathname === '/explorer');
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-2 px-3 py-4 text-sm font-medium border-b-2 transition-colors ${
                    isActive
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className={isExplorerPage ? 'flex-1 overflow-hidden' : 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full'}>
        {children}
      </main>
    </div>
  );
}
