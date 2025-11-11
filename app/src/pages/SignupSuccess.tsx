import { Link } from 'react-router-dom'
import { CheckCircle, ArrowRight } from 'lucide-react'

export default function SignupSuccess() {
  return (
    <div className="min-h-[calc(100vh-200px)] bg-gray-50">
      <div className="container mx-auto px-4 py-12">
        <div className="mx-auto max-w-md">
          <div className="rounded-lg border border-gray-200 bg-white p-8 text-center shadow-sm">
            {/* Success Icon */}
            <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-green-100">
              <CheckCircle className="h-12 w-12 text-green-600" />
            </div>

            {/* Title */}
            <h1 className="mb-3 text-2xl font-bold text-gray-900">
              ¡Cuenta creada exitosamente!
            </h1>

            {/* Description */}
            <p className="mb-8 text-gray-600">
              Tu cuenta ha sido creada correctamente. Ya puedes empezar a explorar nuestros productos.
            </p>

            {/* Actions */}
            <div className="space-y-3">
              <Link
                to="/products"
                className="flex items-center justify-center gap-2 rounded-lg bg-primary-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-primary-700"
              >
                Explorar Productos
                <ArrowRight className="h-5 w-5" />
              </Link>

              <Link
                to="/"
                className="block rounded-lg border border-gray-300 bg-white px-6 py-3 font-semibold text-gray-700 transition-colors hover:bg-gray-50"
              >
                Volver al Inicio
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
