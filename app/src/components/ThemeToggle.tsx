import { Sun, Moon } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'

export default function ThemeToggle() {
  const { isDarkMode, toggleTheme } = useTheme()

  return (
    <button
      onClick={toggleTheme}
      className="relative inline-flex h-9 w-16 items-center rounded-full bg-gray-200 transition-colors hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600"
      aria-label={isDarkMode ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
      title={isDarkMode ? 'Modo claro' : 'Modo oscuro'}
    >
      <span
        className={`inline-flex h-7 w-7 transform items-center justify-center rounded-full bg-white shadow-md transition-transform dark:bg-gray-900 ${
          isDarkMode ? 'translate-x-8' : 'translate-x-1'
        }`}
      >
        {isDarkMode ? (
          <Moon className="h-4 w-4 text-yellow-500" />
        ) : (
          <Sun className="h-4 w-4 text-yellow-600" />
        )}
      </span>
    </button>
  )
}
