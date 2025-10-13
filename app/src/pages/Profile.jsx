import React, { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import ProtectedRoute from '../components/ProtectedRoute'
import '../styles/Profile.css'

function ProfilePageInner() {
  const { user, updateProfile, logout } = useAuth()
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ name: user?.name || '', email: user?.email || '' })

  const handleChange = (e) => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))

  const save = () => {
    updateProfile({ name: form.name, email: form.email })
    setEditing(false)
    alert('Perfil actualizado (mock)')
  }

  const deleteAccount = () => {
    if (!confirm('¿Eliminar cuenta? Esta acción es irreversible en este mock.')) return
    // En este mock, solo hacemos logout y limpiamos user
    logout()
    alert('Cuenta eliminada (mock)')
  }

  if (!user) return null

  return (
    <div className="profile-page">
      <header className="profile-header">
        <h1>Perfil</h1>
        <p>Administra tu información de cuenta</p>
      </header>

      <div className="profile-card">
        <div className="avatar">{user.name?.slice(0,1).toUpperCase()}</div>
        <div className="profile-info">
          {!editing ? (
            <>
              <h2>{user.name}</h2>
              <p className="muted">{user.email}</p>
              <p className="muted small">Miembro desde: {new Date(user.createdAt).toLocaleDateString()}</p>
            </>
          ) : (
            <div className="edit-form">
              <label>Nombre
                <input name="name" value={form.name} onChange={handleChange} />
              </label>
              <label>Email
                <input name="email" value={form.email} onChange={handleChange} />
              </label>
            </div>
          )}
        </div>
        <div className="profile-actions">
          {!editing ? (
            <>
              <button className="btn" onClick={() => { setEditing(true); setForm({ name: user.name, email: user.email }) }}>Editar</button>
              <button className="btn ghost" onClick={() => navigator.clipboard?.writeText(user.email)}>Copiar email</button>
            </>
          ) : (
            <>
              <button className="btn" onClick={save}>Guardar</button>
              <button className="btn ghost" onClick={() => setEditing(false)}>Cancelar</button>
            </>
          )}
          <button className="btn danger" onClick={deleteAccount}>Eliminar cuenta</button>
        </div>
      </div>
    </div>
  )
}

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <ProfilePageInner />
    </ProtectedRoute>
  )
}
