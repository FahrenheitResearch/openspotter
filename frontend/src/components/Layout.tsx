import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/auth'
import clsx from 'clsx'

export default function Layout() {
  const location = useLocation()
  const { isAuthenticated, user, logout } = useAuthStore()

  const navItems = [
    { path: '/', label: 'Map' },
    { path: '/reports', label: 'Reports' },
  ]

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-primary-700 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center space-x-2">
              <svg
                className="w-8 h-8"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="12" cy="12" r="10" />
                <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
                <circle cx="12" cy="12" r="3" />
              </svg>
              <span className="text-xl font-bold">OpenSpotter</span>
            </Link>

            {/* Navigation */}
            <nav className="hidden md:flex items-center space-x-4">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={clsx(
                    'px-3 py-2 rounded-md text-sm font-medium transition-colors',
                    location.pathname === item.path
                      ? 'bg-primary-800 text-white'
                      : 'text-primary-100 hover:bg-primary-600'
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </nav>

            {/* User menu */}
            <div className="flex items-center space-x-4">
              {isAuthenticated ? (
                <>
                  <Link
                    to="/settings"
                    className="text-primary-100 hover:text-white text-sm"
                  >
                    {user?.callsign || user?.email}
                  </Link>
                  <button
                    onClick={logout}
                    className="bg-primary-800 hover:bg-primary-900 px-3 py-2 rounded-md text-sm font-medium"
                  >
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <Link
                    to="/login"
                    className="text-primary-100 hover:text-white text-sm"
                  >
                    Login
                  </Link>
                  <Link
                    to="/register"
                    className="bg-primary-800 hover:bg-primary-900 px-3 py-2 rounded-md text-sm font-medium"
                  >
                    Register
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex flex-col">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-gray-100 border-t">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-center justify-between text-sm text-gray-500">
            <p>OpenSpotter - Open Source Spotter Network</p>
            <div className="flex items-center space-x-4 mt-2 sm:mt-0">
              <a
                href="https://github.com/FahrenheitResearch/openspotter"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-gray-700"
              >
                GitHub
              </a>
              <a href="http://localhost:8000/docs" className="hover:text-gray-700">
                API Docs
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
