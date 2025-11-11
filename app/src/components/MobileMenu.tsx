import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { X, User, Settings, Package, LogOut, LogIn, UserPlus } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

interface MobileMenuProps {
  open: boolean
  onClose: () => void
}

export default function MobileMenu({ open, onClose }: MobileMenuProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const go = (to: string) => {
    onClose()
    navigate(to)
  }

  return (
    <>
      {/* Overlay */}
      <div
        className={`fixed inset-0 z-50 bg-black/50 backdrop-blur-sm transition-opacity lg:hidden ${
          open ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
        onClick={onClose}
      />

      {/* Drawer */}
      <aside
        className={`fixed left-0 top-0 z-50 h-full w-80 transform bg-white shadow-xl transition-transform duration-300 lg:hidden ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 p-4">
          <h3 className="text-lg font-semibold text-gray-900">Menú</h3>
          <button
            onClick={onClose}
            className="rounded-md p-2 hover:bg-gray-100"
            aria-label="Cerrar menú"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* User Info */}
        <div className="border-b border-gray-200 p-4">
          {user ? (
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-600 text-lg font-bold text-white">
                {user.name?.slice(0, 1).toUpperCase()}
              </div>
              <div className="flex-1 overflow-hidden">
                <div className="truncate font-medium text-gray-900">{user.name}</div>
                <div className="truncate text-sm text-gray-600">{user.email}</div>
              </div>
            </div>
          ) : (
            <div className="text-gray-600">Invitado</div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-4">
          <div className="space-y-1">
            <button
              onClick={() => go('/products')}
              className="flex w-full items-center gap-3 rounded-md px-4 py-3 text-left text-gray-700 hover:bg-gray-100"
            >
              <Package className="h-5 w-5" />
              <span>Productos</span>
            </button>

            {user && (
              <>
                <button
                  onClick={() => go('/profile')}
                  className="flex w-full items-center gap-3 rounded-md px-4 py-3 text-left text-gray-700 hover:bg-gray-100"
                >
                  <User className="h-5 w-5" />
                  <span>Perfil</span>
                </button>
                <button
                  onClick={() => go('/settings')}
                  className="flex w-full items-center gap-3 rounded-md px-4 py-3 text-left text-gray-700 hover:bg-gray-100"
                >
                  <Settings className="h-5 w-5" />
                  <span>Configuración</span>
                </button>
              </>
            )}
          </div>
        </nav>

        {/* Footer Actions */}
        <div className="border-t border-gray-200 p-4">
          {user ? (
            <button
              onClick={() => {
                logout()
                onClose()
                navigate('/')
              }}
              className="flex w-full items-center justify-center gap-2 rounded-md bg-red-600 px-4 py-3 font-medium text-white hover:bg-red-700"
            >
              <LogOut className="h-5 w-5" />
              <span>Cerrar Sesión</span>
            </button>
          ) : (
            <div className="space-y-2">
              <button
                onClick={() => go('/login')}
                className="flex w-full items-center justify-center gap-2 rounded-md border border-gray-300 px-4 py-3 font-medium text-gray-700 hover:bg-gray-100"
              >
                <LogIn className="h-5 w-5" />
                <span>Entrar</span>
              </button>
              <button
                onClick={() => go('/signup')}
                className="flex w-full items-center justify-center gap-2 rounded-md bg-primary-600 px-4 py-3 font-medium text-white hover:bg-primary-700"
              >
                <UserPlus className="h-5 w-5" />
                <span>Registrarse</span>
              </button>
            </div>
          )}
        </div>
      </aside>
    </>
  )
}
