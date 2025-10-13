import React, { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import ThemeToggle from '../components/ThemeToggle'
import '../styles/Settings.css'

export default function Settings() {
  const { user } = useAuth()
  const { isDarkMode, toggleTheme } = useTheme()

  const [settings, setSettings] = useState(() => ({
    language: localStorage.getItem('language') || 'es',
    currency: localStorage.getItem('currency') || 'MXN',
    notifications: {
      push: localStorage.getItem('pushNotifications') !== 'false',
      email: localStorage.getItem('emailNotifications') !== 'false',
      sms: localStorage.getItem('smsNotifications') === 'true'
    },
    display: {
      compactView: localStorage.getItem('compactView') === 'true',
      showPrices: localStorage.getItem('showPrices') !== 'false',
      autoplay: localStorage.getItem('autoplay') !== 'false'
    },
    accent: localStorage.getItem('accent') || getComputedStyle(document.documentElement).getPropertyValue('--accent') || '#85E3FF',
    fontSize: localStorage.getItem('fontSize') || '16'
  }))

  useEffect(() => {
    document.documentElement.style.setProperty('--accent', settings.accent)
    localStorage.setItem('accent', settings.accent)
  }, [settings.accent])

  useEffect(() => {
    document.documentElement.style.setProperty('--base-font-size', `${settings.fontSize}px`)
    localStorage.setItem('fontSize', settings.fontSize)
  }, [settings.fontSize])

  const handleLanguageChange = (e) => {
    const language = e.target.value
    setSettings(prev => ({ ...prev, language }))
    localStorage.setItem('language', language)
  }

  const handleCurrencyChange = (e) => {
    const currency = e.target.value
    setSettings(prev => ({ ...prev, currency }))
    localStorage.setItem('currency', currency)
  }

  const handleNotificationChange = (type) => {
    const newVal = !settings.notifications[type]
    setSettings(prev => ({
      ...prev,
      notifications: { ...prev.notifications, [type]: newVal }
    }))
    localStorage.setItem(`${type}Notifications`, String(newVal))
  }

  const handleDisplayChange = (type) => {
    const newVal = !settings.display[type]
    setSettings(prev => ({ ...prev, display: { ...prev.display, [type]: newVal } }))
    localStorage.setItem(type, String(newVal))
  }

  const handleAccentChange = (e) => setSettings(prev => ({ ...prev, accent: e.target.value }))
  const handleFontSizeChange = (e) => setSettings(prev => ({ ...prev, fontSize: e.target.value }))

  const clearCache = () => {
    if (!confirm('¿Limpiar caché? Se borrarán datos temporales.')) return
    const keep = ['language', 'currency', 'theme']
    const keepValues = {}
    keep.forEach(k => { if (localStorage.getItem(k)) keepValues[k] = localStorage.getItem(k) })
    localStorage.clear()
    Object.entries(keepValues).forEach(([k, v]) => localStorage.setItem(k, v))
    alert('Caché limpiado')
    window.location.reload()
  }

  const resetDefaults = () => {
    if (!confirm('¿Restablecer configuración a los valores por defecto?')) return
    localStorage.removeItem('theme')
    localStorage.removeItem('accent')
    localStorage.removeItem('fontSize')
    localStorage.removeItem('language')
    localStorage.removeItem('currency')
    localStorage.removeItem('pushNotifications')
    localStorage.removeItem('emailNotifications')
    localStorage.removeItem('smsNotifications')
    window.location.reload()
  }

  return (
    <div className="settings-page">
      <div className="settings-container">
        <header className="settings-header">
          <h1>Configuración</h1>
          <p>Personaliza tu experiencia en La Tiendita</p>
        </header>

        <section className="settings-section">
          <div className="section-header">
            <h2>🎨 Apariencia</h2>
            <p>Personaliza el aspecto visual</p>
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <label>Tema</label>
              <span>Alternar entre modo claro y oscuro</span>
            </div>
            <ThemeToggle />
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <label>Color de acento</label>
              <span>Color usado en botones y elementos interactivos</span>
            </div>
            <input type="color" value={settings.accent} onChange={handleAccentChange} />
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <label>Tamaño de fuente</label>
              <span>Ajusta la base de tamaño de fuente</span>
            </div>
            <div className="font-control">
              <output>{settings.fontSize}px</output>
              <input type="range" min="12" max="22" value={settings.fontSize} onChange={handleFontSizeChange} />
            </div>
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <label>Vista compacta</label>
              <span>Mostrar más contenido en pantalla</span>
            </div>
            <label className="toggle-switch">
              <input type="checkbox" checked={settings.display.compactView} onChange={() => handleDisplayChange('compactView')} />
              <span className="slider" />
            </label>
          </div>
        </section>

        <section className="settings-section">
          <div className="section-header">
            <h2>🌍 Idioma y Región</h2>
            <p>Configuración regional y de idioma</p>
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <label>Idioma</label>
              <span>Idioma de la interfaz</span>
            </div>
            <select value={settings.language} onChange={handleLanguageChange} className="setting-select">
              <option value="es">Español</option>
              <option value="en">English</option>
              <option value="fr">Français</option>
            </select>
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <label>Moneda</label>
              <span>Moneda para mostrar precios</span>
            </div>
            <select value={settings.currency} onChange={handleCurrencyChange} className="setting-select">
              <option value="MXN">MXN - Peso Mexicano</option>
              <option value="USD">USD - Dólar Americano</option>
              <option value="EUR">EUR - Euro</option>
            </select>
          </div>
        </section>

        <section className="settings-section">
          <div className="section-header">
            <h2>🔔 Notificaciones</h2>
            <p>Gestiona cómo quieres recibir notificaciones</p>
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <label>Push</label>
              <span>Alertas en tiempo real en el navegador</span>
            </div>
            <label className="toggle-switch">
              <input type="checkbox" checked={settings.notifications.push} onChange={() => handleNotificationChange('push')} />
              <span className="slider" />
            </label>
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <label>Email</label>
              <span>Ofertas y actualizaciones por correo</span>
            </div>
            <label className="toggle-switch">
              <input type="checkbox" checked={settings.notifications.email} onChange={() => handleNotificationChange('email')} />
              <span className="slider" />
            </label>
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <label>SMS</label>
              <span>Alertas importantes por mensaje</span>
            </div>
            <label className="toggle-switch">
              <input type="checkbox" checked={settings.notifications.sms} onChange={() => handleNotificationChange('sms')} />
              <span className="slider" />
            </label>
          </div>
        </section>

        {user && (
          <section className="settings-section">
            <div className="section-header">
              <h2>👤 Cuenta</h2>
              <p>Información y configuración de tu cuenta</p>
            </div>
            <div className="setting-item">
              <div className="setting-info">
                <label>Usuario</label>
                <span>{user.email}</span>
              </div>
              <span className="user-badge">Verificado</span>
            </div>
            <div className="setting-item">
              <div className="setting-info">
                <label>Nombre</label>
                <span>{user.name}</span>
              </div>
              <button className="edit-button">Editar</button>
            </div>
          </section>
        )}

        <section className="settings-section">
          <div className="section-header">
            <h2>⚙️ Sistema</h2>
            <p>Configuraciones avanzadas y mantenimiento</p>
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <label>Limpiar caché</label>
              <span>Borra datos temporales para liberar espacio</span>
            </div>
            <button onClick={clearCache} className="clear-button">Limpiar</button>
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <label>Restablecer</label>
              <span>Restablece preferencias al estado inicial</span>
            </div>
            <button onClick={resetDefaults} className="clear-button">Restablecer</button>
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <label>Versión</label>
              <span>La Tiendita v1.0.0</span>
            </div>
            <span className="version-badge">Actualizado</span>
          </div>
        </section>

        <section className="settings-section">
          <div className="section-header">
            <h2>❓ Ayuda y Soporte</h2>
            <p>Obtén ayuda y contacta con nosotros</p>
          </div>
          <div className="help-links">
            <a href="#" className="help-link">
              <span>📖</span>
              <div>
                <strong>Centro de ayuda</strong>
                <small>Preguntas frecuentes y guías</small>
              </div>
            </a>
            <a href="#" className="help-link">
              <span>💬</span>
              <div>
                <strong>Contactar soporte</strong>
                <small>Habla con nuestro equipo</small>
              </div>
            </a>
            <a href="#" className="help-link">
              <span>⭐</span>
              <div>
                <strong>Califica la app</strong>
                <small>Comparte tu experiencia</small>
              </div>
            </a>
          </div>
        </section>
      </div>
    </div>
  )
}