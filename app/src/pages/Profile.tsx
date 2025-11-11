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
      <div className="container mx-auto px-4 py-12">
        <div className="mx-auto max-w-3xl">
          {/* Header */}
          <div className="mb-8 rounded-lg border border-gray-200 bg-white p-8 text-center">
            <div className="mx-auto mb-4 flex h-24 w-24 items-center justify-center rounded-full bg-primary-600 text-4xl font-bold text-white">
              {user.name?.charAt(0).toUpperCase()}
            </div>
            <h1 className="mb-2 text-3xl font-bold text-gray-900">{user.name}</h1>
            <p className="text-gray-600">{user.email}</p>
          </div>

          {/* Information */}
          <div className="rounded-lg border border-gray-200 bg-white p-8">
            <div className="mb-6 flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">Información Personal</h2>
              <button className="flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
                <Edit2 className="h-4 w-4" />
                Editar
              </button>
            </div>

            <div className="space-y-4">
              <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
                <User className="h-5 w-5 text-gray-600" />
                <div>
                  <p className="text-sm text-gray-600">Nombre</p>
                  <p className="font-medium text-gray-900">{user.name}</p>
                </div>
              </div>

              <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
                <Mail className="h-5 w-5 text-gray-600" />
                <div>
                  <p className="text-sm text-gray-600">Correo Electrónico</p>
                  <p className="font-medium text-gray-900">{user.email}</p>
                </div>
              </div>

              {user.customer_id && (
                <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
                  <MapPin className="h-5 w-5 text-gray-600" />
                  <div>
                    <p className="text-sm text-gray-600">ID de Cliente</p>
                    <p className="font-medium text-gray-900">{user.customer_id}</p>
                  </div>
                </div>
              )}

              {(typeof user.createdAt === 'string' ||
                typeof user.createdAt === 'number' ||
                user.createdAt instanceof Date) && (
                <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
                  <Calendar className="h-5 w-5 text-gray-600" />
                  <div>
                    <p className="text-sm text-gray-600">Miembro desde</p>
                    <p className="font-medium text-gray-900">
                      {new Date(user.createdAt as string | number | Date).toLocaleDateString('es-ES', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                      })}
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div className="mt-6 pt-6 border-t border-gray-200">
              <button
                onClick={() => {
                  logout()
                  navigate('/')
                }}
                className="w-full rounded-lg bg-red-600 px-6 py-3 font-semibold text-white hover:bg-red-700"
              >
                Cerrar Sesión
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
