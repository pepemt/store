import { Link } from 'react-router-dom'
import { Mail, Phone, MapPin, Facebook, Instagram, Twitter, Package } from 'lucide-react'

export default function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="border-t border-gray-200 bg-gray-50">
      <div className="container mx-auto px-4 py-12">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-4">
          {/* Brand */}
          <div>
            <Link to="/" className="mb-4 flex items-center gap-2 text-xl font-bold text-primary-600">
              <Package className="h-6 w-6" />
              <span>La Tiendita</span>
            </Link>
            <p className="mb-4 text-sm text-gray-600">
              Tu tienda de confianza con los mejores productos al mejor precio. Calidad garantizada y envío rápido.
            </p>
            <div className="flex gap-3">
              <a
                href="#"
                className="rounded-full bg-gray-200 p-2 text-gray-600 hover:bg-primary-600 hover:text-white"
                aria-label="Facebook"
              >
                <Facebook className="h-4 w-4" />
              </a>
              <a
                href="#"
                className="rounded-full bg-gray-200 p-2 text-gray-600 hover:bg-primary-600 hover:text-white"
                aria-label="Instagram"
              >
                <Instagram className="h-4 w-4" />
              </a>
              <a
                href="#"
                className="rounded-full bg-gray-200 p-2 text-gray-600 hover:bg-primary-600 hover:text-white"
                aria-label="Twitter"
              >
                <Twitter className="h-4 w-4" />
              </a>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="mb-4 font-semibold text-gray-900">Enlaces Rápidos</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link to="/" className="text-gray-600 hover:text-primary-600">
                  Inicio
                </Link>
              </li>
              <li>
                <Link to="/products" className="text-gray-600 hover:text-primary-600">
                  Productos
                </Link>
              </li>
              <li>
                <Link to="/cart" className="text-gray-600 hover:text-primary-600">
                  Carrito
                </Link>
              </li>
              <li>
                <Link to="/chat" className="text-gray-600 hover:text-primary-600">
                  Ayuda
                </Link>
              </li>
            </ul>
          </div>

          {/* Customer Service */}
          <div>
            <h4 className="mb-4 font-semibold text-gray-900">Atención al Cliente</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link to="/profile" className="text-gray-600 hover:text-primary-600">
                  Mi Cuenta
                </Link>
              </li>
              <li>
                <a href="#" className="text-gray-600 hover:text-primary-600">
                  Seguimiento de Orden
                </a>
              </li>
              <li>
                <a href="#" className="text-gray-600 hover:text-primary-600">
                  Devoluciones
                </a>
              </li>
              <li>
                <a href="#" className="text-gray-600 hover:text-primary-600">
                  Preguntas Frecuentes
                </a>
              </li>
            </ul>
          </div>

          {/* Contact */}
          <div>
            <h4 className="mb-4 font-semibold text-gray-900">Contacto</h4>
            <ul className="space-y-3 text-sm text-gray-600">
              <li className="flex items-start gap-3">
                <Mail className="h-5 w-5 text-primary-600" />
                <span>info@latiendita.com</span>
              </li>
              <li className="flex items-start gap-3">
                <Phone className="h-5 w-5 text-primary-600" />
                <span>+1 (555) 123-4567</span>
              </li>
              <li className="flex items-start gap-3">
                <MapPin className="h-5 w-5 text-primary-600" />
                <span>Esquina Principal #123<br />Ciudad, País</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-12 border-t border-gray-200 pt-8">
          <div className="flex flex-col items-center justify-between gap-4 text-sm text-gray-600 sm:flex-row">
            <p>© {currentYear} La Tiendita. Todos los derechos reservados.</p>
            <div className="flex gap-4">
              <a href="#" className="hover:text-primary-600">
                Términos de Servicio
              </a>
              <a href="#" className="hover:text-primary-600">
                Política de Privacidad
              </a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}
