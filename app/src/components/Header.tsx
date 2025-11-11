import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Search, ShoppingCart, Menu, User, LogOut, Package } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useCart } from '../context/CartContext'
import MobileMenu from './MobileMenu'
import { Button } from './ui/button'
import { Input } from './ui/input'

export default function Header() {
  const { user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const { count } = useCart()
  const navigate = useNavigate()

  const handleSearch = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const q = formData.get('q') || ''
    const qs = q.toString().trim() ? `?q=${encodeURIComponent(q.toString().trim())}` : ''
    navigate(`/products${qs}`)
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b border-gray-200 bg-white shadow-sm">
      {/* Top Bar */}
      <div style={{ backgroundColor: '#6e348d' }} className="text-white shadow-md">
        <div className="container mx-auto px-4 py-2.5">
          <div className="flex items-center justify-between text-sm font-medium">
            <p className="hidden sm:block">Envío gratis en compras mayores a $500</p>
            <div className="ml-auto flex items-center gap-4">
              <Link to="/chat" className="hover:underline transition-opacity hover:opacity-80">Ayuda</Link>
            </div>
          </div>
        </div>
      </div>

      {/* Main Header */}
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center gap-4">
          {/* Mobile Menu Button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMenuOpen(true)}
            className="lg:hidden"
            aria-label="Abrir menú"
          >
            <Menu className="h-6 w-6" />
          </Button>

          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 text-2xl font-bold text-primary-600">
            <Package className="h-8 w-8" />
            <span className="hidden sm:block">La Tiendita</span>
          </Link>

          {/* Search Bar - Desktop */}
          <form onSubmit={handleSearch} className="hidden flex-1 md:flex md:max-w-2xl">
            <div className="relative flex w-full shadow-sm">
              <Input
                name="q"
                type="text"
                placeholder="Buscar productos..."
                className="flex-1 rounded-r-none border-r-0 focus-visible:ring-2 focus-visible:ring-[#6e348d] border-gray-300"
                style={{ borderColor: '#d1d5db' }}
              />
              <Button
                type="submit"
                className="rounded-l-none shadow-sm text-white"
                style={{ backgroundColor: '#6e348d' }}
              >
                <Search className="h-5 w-5" />
              </Button>
            </div>
          </form>

          {/* Navigation */}
          <nav className="ml-auto hidden items-center gap-2 lg:flex">
            <Button variant="ghost" asChild>
              <Link to="/products">Productos</Link>
            </Button>

            {user ? (
              <div className="flex items-center gap-2">
                <Button variant="ghost" asChild>
                  <Link to="/profile" className="flex items-center gap-2">
                    <User className="h-5 w-5" />
                    <span className="hidden xl:block">{user.name}</span>
                  </Link>
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    logout()
                    navigate('/')
                  }}
                  title="Cerrar sesión"
                >
                  <LogOut className="h-5 w-5" />
                </Button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Button variant="ghost" asChild>
                  <Link to="/login">Entrar</Link>
                </Button>
                <Button asChild className="shadow-sm" style={{ backgroundColor: '#6e348d', color: 'white' }}>
                  <Link to="/signup">Registrarse</Link>
                </Button>
              </div>
            )}

            {/* Cart */}
            <Button variant="ghost" asChild className="relative">
              <Link to="/cart" className="flex items-center gap-2">
                <ShoppingCart className="h-5 w-5" />
                <span className="hidden xl:block">Carrito</span>
                {count > 0 && (
                  <span className="absolute -right-1 -top-1 flex h-5 min-w-[20px] items-center justify-center rounded-full shadow-sm px-1.5 text-xs font-bold text-white" style={{ backgroundColor: '#6e348d' }}>
                    {count}
                  </span>
                )}
              </Link>
            </Button>
          </nav>
        </div>

        {/* Mobile Search */}
        <form onSubmit={handleSearch} className="mt-4 md:hidden">
          <div className="relative flex shadow-sm">
            <Input
              name="q"
              type="text"
              placeholder="Buscar productos..."
              className="flex-1 rounded-r-none border-r-0 focus-visible:ring-2 focus-visible:ring-[#6e348d] border-gray-300"
              style={{ borderColor: '#d1d5db' }}
            />
            <Button
              type="submit"
              size="icon"
              className="rounded-l-none shadow-sm"
              style={{ backgroundColor: '#6e348d' }}
            >
              <Search className="h-5 w-5" />
            </Button>
          </div>
        </form>
      </div>

      <MobileMenu open={menuOpen} onClose={() => setMenuOpen(false)} />
    </header>
  )
}
