import React, { useEffect } from 'react'
import { Link } from 'react-router-dom'
import '../styles/SignupSuccess.css'

export default function SignupSuccess() {
  useEffect(() => {
    const confettiContainer = document.querySelector('.confetti')

    // Asegurarse de que no haya duplicados al volver a la página
    confettiContainer.innerHTML = ''

    for (let i = 0; i < 40; i++) {
      const confetti = document.createElement('div')
      confetti.classList.add('confetti-piece')

      // Color aleatorio
      confetti.style.setProperty('--hue', Math.floor(Math.random() * 360))

      // Posición horizontal aleatoria
      confetti.style.left = Math.random() * 100 + 'vw'

      // Duración de caída aleatoria
      confetti.style.animationDuration = 3 + Math.random() * 2 + 's'

      // Retardo para dispersión
      confetti.style.animationDelay = Math.random() * 2 + 's'

      confettiContainer.appendChild(confetti)
    }
  }, [])

  return (
    <div className="success-container">
      <div className="confetti"></div>

      <div className="success-card">
        <div className="success-icon">🎉</div>
        <h2 className="success-title">¡Registro exitoso!</h2>
        <p className="success-message">
          Tu cuenta ha sido creada correctamente.  
          Ahora puedes iniciar sesión para comenzar a explorar <b>La Tiendita</b>.
        </p>
        <Link to="/login" className="success-button">
          Ir a iniciar sesión
        </Link>
      </div>
    </div>
  )
}
