import { BrowserRouter, Routes, Route } from 'react-router-dom'

import { AuthProvider } from './context/AuthContext'
import { CartProvider } from './context/CartContext'
import { ChatProvider } from './context/ChatContext'
import Header from './components/Header'
import Footer from './components/Footer'
import Chat from './components/Chat'
import ProtectedRoute from './components/ProtectedRoute'
import { Toaster } from './components/ui/sonner'

import Landing from './pages/Landing'
import Login from './pages/Login'
import Signup from './pages/Signup'
import ProductList from './pages/ProductList'
import ProductDetails from './pages/ProductDetails'
import Cart from './pages/Cart'
import Settings from './pages/Settings'
import Profile from './pages/Profile'
import Checkout from './pages/Checkout'
import CheckoutSuccess from './pages/CheckoutSuccess'
import CheckoutCancel from './pages/CheckoutCancel'
import Orders from './pages/Orders'
import OrderDetail from './pages/OrderDetail'
import SignupSuccess from './pages/SignupSuccess'

function App() {
  return (
    <AuthProvider>
      <CartProvider>
        <ChatProvider>
          <BrowserRouter>
            <div className="flex min-h-screen flex-col bg-white">
              <Header />
              <main className="flex-1">
                <Routes>
                  <Route path="/" element={<Landing />} />
                  <Route path="/login" element={<Login />} />
                  <Route path="/signup" element={<Signup />} />
                  <Route path="/signup-success" element={<SignupSuccess />} />
                  <Route path="/products" element={<ProductList />} />
                  <Route path="/product/:id" element={<ProductDetails />} />
                  <Route
                    path="/cart"
                    element={
                      <ProtectedRoute>
                        <Cart />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/checkout"
                    element={
                      <ProtectedRoute>
                        <Checkout />
                      </ProtectedRoute>
                    }
                  />
                  <Route path="/checkout/success" element={<CheckoutSuccess />} />
                  <Route path="/checkout/cancel" element={<CheckoutCancel />} />
                  <Route
                    path="/orders"
                    element={
                      <ProtectedRoute>
                        <Orders />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/orders/:id"
                    element={
                      <ProtectedRoute>
                        <OrderDetail />
                      </ProtectedRoute>
                    }
                  />
                  <Route path="/profile" element={<Profile />} />
                  <Route path="/settings" element={<Settings />} />
                </Routes>
              </main>
              <Footer />
              <Chat />
              <Toaster />
            </div>
          </BrowserRouter>
        </ChatProvider>
      </CartProvider>
    </AuthProvider>
  )
}

export default App
