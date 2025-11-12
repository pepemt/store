import { User, Mail, Calendar, MapPin, Edit2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'

export default function Profile() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  if (!user) {
    navigate('/login')
    return null
  }

  return (
    <div className="min-h-[calc(100vh-200px)] bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <div className="mx-auto max-w-4xl">
          <h1 className="mb-6 text-3xl font-bold text-gray-900">Mi Perfil</h1>

          <div className="grid gap-6 lg:grid-cols-3">
            {/* Sidebar with Avatar and Quick Actions */}
            <div className="lg:col-span-1">
              <div className="rounded-lg border border-gray-200 bg-white p-6">
                {/* Avatar */}
                <div className="mb-6 text-center">
                  <div className="mx-auto mb-4 flex h-24 w-24 items-center justify-center rounded-full bg-primary-600 text-4xl font-bold text-white shadow-lg">
                    {user.name?.charAt(0).toUpperCase()}
                  </div>
                  <h2 className="text-xl font-bold text-gray-900">{user.name}</h2>
                  <p className="mt-1 text-sm text-gray-600">{user.email}</p>
                </div>

                {/* Member Badge */}
                {(typeof user.createdAt === 'string' ||
                  typeof user.createdAt === 'number' ||
                  user.createdAt instanceof Date) && (
                  <div className="mb-6 rounded-lg bg-primary-50 p-4 text-center">
                    <Calendar className="mx-auto mb-2 h-5 w-5 text-primary-600" />
                    <p className="text-xs text-gray-600">Miembro desde</p>
                    <p className="mt-1 text-sm font-semibold text-gray-900">
                      {new Date(user.createdAt as string | number | Date).toLocaleDateString('es-ES', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                      })}
                    </p>
                  </div>
                )}

                {/* Quick Actions */}
                <div className="space-y-2">
                  <button className="flex w-full items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50">
                    <Edit2 className="h-4 w-4" />
                    Editar Perfil
                  </button>
                  <button
                    onClick={() => {
                      logout()
                      navigate('/')
                    }}
                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-red-700"
                  >
                    Cerrar Sesión
                  </button>
                </div>
              </div>
            </div>

            {/* Main Content */}
            <div className="lg:col-span-2 space-y-6">
              {/* Personal Information */}
              <div className="rounded-lg border border-gray-200 bg-white p-6">
                <h3 className="mb-4 flex items-center gap-2 text-lg font-bold text-gray-900">
                  <User className="h-5 w-5 text-primary-600" />
                  Información Personal
                </h3>

                <div className="space-y-3">
                  <div className="flex items-start justify-between border-b border-gray-100 pb-3">
                    <div>
                      <p className="text-sm font-medium text-gray-600">Nombre Completo</p>
                      <p className="mt-1 text-base text-gray-900">{user.name || 'No especificado'}</p>
                    </div>
                  </div>

                  <div className="flex items-start justify-between border-b border-gray-100 pb-3">
                    <div>
                      <p className="text-sm font-medium text-gray-600">Correo Electrónico</p>
                      <p className="mt-1 text-base text-gray-900">{user.email}</p>
                    </div>
                  </div>

                  {user.customer_id && (
                    <div className="flex items-start justify-between border-b border-gray-100 pb-3">
                      <div>
                        <p className="text-sm font-medium text-gray-600">ID de Cliente</p>
                        <p className="mt-1 font-mono text-sm text-gray-900">{user.customer_id}</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Account Settings */}
              <div className="rounded-lg border border-gray-200 bg-white p-6">
                <h3 className="mb-4 flex items-center gap-2 text-lg font-bold text-gray-900">
                  <MapPin className="h-5 w-5 text-primary-600" />
                  Información de Cuenta
                </h3>

                <div className="space-y-3">
                  <div className="rounded-lg bg-gray-50 p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-700">Estado de la cuenta</p>
                        <p className="mt-1 text-sm text-green-600">✓ Activa</p>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-lg bg-gray-50 p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-700">Email verificado</p>
                        <p className="mt-1 text-sm text-green-600">✓ Verificado</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
