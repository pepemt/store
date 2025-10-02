import React from 'react'
import '../styles/Footer.css'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-container">
        <div className="footer-content">
          {/* Logo y descripción */}
          <div className="footer-brand">
            <h3 className="footer-logo">
              🛒 La Tiendita de la Esquina
            </h3>
            <p className="footer-description">
              Tu tienda de confianza con los mejores productos al mejor precio. 
              Calidad garantizada y envío rápido a toda la ciudad.
            </p>
            <div className="social-links">
              <a href="#" className="social-link facebook">📘</a>
              <a href="#" className="social-link instagram">📷</a>
              <a href="#" className="social-link twitter">🐦</a>
            </div>
          </div>

          {/* Enlaces rápidos */}
          <div>
            <h4>Enlaces Rápidos</h4>
            <ul className="footer-links">
              <li><a href="#">Inicio</a></li>
              <li><a href="#">Productos</a></li>
              <li><a href="#">Ofertas</a></li>
              <li><a href="#">Contacto</a></li>
            </ul>
          </div>

          {/* Información de contacto */}
          <div>
            <h4>Contacto</h4>
            <ul className="contact-info">
              <li>
                <span className="contact-icon">📧</span>
                <span>info@latiendita.com</span>
              </li>
              <li>
                <span className="contact-icon">📞</span>
                <span>+1 (555) 123-4567</span>
              </li>
              <li>
                <span className="contact-icon">📍</span>
                <span>Esquina Principal #123</span>
              </li>
            </ul>
          </div>
        </div>

        <div className="footer-bottom">
          <div className="footer-bottom-content">
            <div className="footer-copyright">
              © {new Date().getFullYear()} La Tiendita de la Esquina — Proyecto demo
            </div>
            <div className="footer-credits">
              Hecho con ❤️ para desarrollo y pruebas
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}