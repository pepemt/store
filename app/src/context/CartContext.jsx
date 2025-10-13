import React, { createContext, useContext, useState, useEffect } from 'react'

const CartContext = createContext()

export const CartProvider = ({ children }) => {
  const [items, setItems] = useState(() => {
    try { return JSON.parse(localStorage.getItem('tiendita_cart') || '[]') } catch { return [] }
  })

  useEffect(() => {
    localStorage.setItem('tiendita_cart', JSON.stringify(items))
  }, [items])

  const add = (product, qty = 1) => {
    setItems(prev => {
      const idx = prev.findIndex(i => i.id === product.id)
      if (idx === -1) return [...prev, { ...product, qty }]
      const next = [...prev]
      next[idx].qty = Math.min((next[idx].qty || 0) + qty, product.stock || 9999)
      return next
    })
  }

  const remove = (id) => setItems(prev => prev.filter(i => i.id !== id))

  const updateQty = (id, qty) => {
    setItems(prev => prev.map(i => i.id === id ? { ...i, qty: Math.max(1, qty) } : i))
  }

  const clear = () => setItems([])

  const total = items.reduce((s, it) => s + (it.price || 0) * (it.qty || 0), 0)

  const count = items.reduce((s, it) => s + (it.qty || 0), 0)

  return (
    <CartContext.Provider value={{ items, add, remove, updateQty, clear, total, count }}>
      {children}
    </CartContext.Provider>
  )
}

export const useCart = () => useContext(CartContext)
export default CartContext
