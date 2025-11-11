import { Bell, Lock, Globe } from 'lucide-react'

export default function Settings() {
  return (
    <div className="min-h-[calc(100vh-200px)] bg-gray-50">
      <div className="container mx-auto px-4 py-12">
        <div className="mx-auto max-w-3xl">
          <h1 className="mb-8 text-3xl font-bold text-gray-900">Configuración</h1>

          {/* Notifications */}
          <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6">
            <div className="mb-4 flex items-center gap-3">
              <Bell className="h-6 w-6 text-primary-600" />
              <h2 className="text-xl font-bold text-gray-900">Notificaciones</h2>
            </div>

            <div className="space-y-4">
              <label className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">Notificaciones por correo</p>
                  <p className="text-sm text-gray-600">Recibe actualizaciones de pedidos</p>
                </div>
                <input type="checkbox" className="h-5 w-5 rounded border-gray-300 text-primary-600" defaultChecked />
              </label>

              <label className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">Promociones</p>
                  <p className="text-sm text-gray-600">Recibe ofertas exclusivas</p>
                </div>
                <input type="checkbox" className="h-5 w-5 rounded border-gray-300 text-primary-600" />
              </label>
            </div>
          </div>

          {/* Security */}
          <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6">
            <div className="mb-4 flex items-center gap-3">
              <Lock className="h-6 w-6 text-primary-600" />
              <h2 className="text-xl font-bold text-gray-900">Seguridad</h2>
            </div>

            <div className="space-y-3">
              <button className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-left font-medium text-gray-700 hover:bg-gray-50">
                Cambiar Contraseña
              </button>
              <button className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-left font-medium text-gray-700 hover:bg-gray-50">
                Autenticación de Dos Factores
              </button>
            </div>
          </div>

          {/* Language */}
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <div className="mb-4 flex items-center gap-3">
              <Globe className="h-6 w-6 text-primary-600" />
              <h2 className="text-xl font-bold text-gray-900">Idioma y Región</h2>
            </div>

            <select className="w-full rounded-lg border border-gray-300 px-4 py-3 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500">
              <option value="es">Español</option>
              <option value="en">English</option>
              <option value="fr">Français</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  )
}
