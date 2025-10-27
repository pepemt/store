import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'

import { AuthProvider } from './context/AuthContext'
import { CartProvider } from './context/CartContext'
import { ChatProvider } from './context/ChatContext'
import { ThemeProvider } from './context/ThemeContext'
import Header from './components/Header'
import Footer from './components/Footer'
import Chat from './components/Chat'
import ProtectedRoute from './components/ProtectedRoute'
import './styles/App.css'

// Páginas
import Landing from './pages/Landing'
import Login from './pages/Login'
import Signup from './pages/Signup'
import ProductList from './pages/ProductList'
import ProductDetails from './pages/ProductDetails'
import Cart from './pages/Cart'
import Settings from './pages/Settings'
import Profile from './pages/Profile'
import Checkout from './pages/Checkout'
import ChatPage from './pages/ChatPage'
import SignupSuccess from './pages/SignupSuccess'

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <CartProvider>
          <ChatProvider>
            <BrowserRouter>
            <div className="app">
            <Header />
            <main className="main-content">
              <Routes>
                <Route path="/" element={<Landing />} />
                <Route path="/login" element={<Login />} />
                <Route path="/signup" element={<Signup />} />
                <Route path="/signup-success" element={<SignupSuccess />} />
                <Route path="/products" element={<ProductList />} />
                <Route path="/product/:id" element={<ProductDetails />} />
                <Route path="/chat" element={<ChatPage />} />
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
                <Route path="/profile" element={<Profile />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </main>
            <Footer />
            <Chat />
          </div>
        </BrowserRouter>
        </ChatProvider>
      </CartProvider>
    </AuthProvider>
    </ThemeProvider>
  )
}

export default App
