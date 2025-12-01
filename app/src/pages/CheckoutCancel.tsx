import { useNavigate } from 'react-router-dom'
import { XCircle, ShoppingCart, ArrowLeft } from 'lucide-react'

export default function CheckoutCancel() {
  const navigate = useNavigate()

  return (
    <div className="flex min-h-[calc(100vh-200px)] items-center justify-center bg-gray-50">
      <div className="mx-auto max-w-md rounded-lg border border-gray-200 bg-white p-8 text-center">
        <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-red-100">
          <XCircle className="h-12 w-12 text-red-600" />
        </div>

        <h2 className="mb-3 text-2xl font-bold text-gray-900">Pago Cancelado</h2>

        <p className="mb-6 text-gray-600">
          Tu pago ha sido cancelado. No se ha realizado ningún cargo a tu tarjeta.
          Los productos siguen en tu carrito si deseas intentarlo nuevamente.
        </p>

        <div className="flex flex-col gap-3">
          <button
            onClick={() => navigate('/cart')}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-6 py-3 font-medium text-white hover:bg-primary-700"
          >
            <ShoppingCart className="h-4 w-4" />
            Volver al carrito
          </button>

          <button
            onClick={() => navigate('/')}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-gray-300 px-6 py-3 font-medium text-gray-700 hover:bg-gray-50"
          >
            <ArrowLeft className="h-4 w-4" />
            Seguir comprando
          </button>
        </div>
      </div>
    </div>
  )
}
