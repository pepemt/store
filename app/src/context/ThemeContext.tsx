import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface ThemeContextType {
  isDarkMode: boolean
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

interface ThemeProviderProps {
  children: ReactNode
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  // Always start in light mode, ignore system preference
  const [isDarkMode, setIsDarkMode] = useState(false)

  useEffect(() => {
    // Always use light mode, do not detect system preference
    // If you want to enable dark mode in the future, uncomment the code below
    // const savedTheme = localStorage.getItem('theme')
    // if (savedTheme) {
    //   setIsDarkMode(savedTheme === 'dark')
    // } else {
    //   const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    //   setIsDarkMode(prefersDark)
    // }

    // Force light mode
    setIsDarkMode(false)
  }, [])

  useEffect(() => {
    // Always keep light mode active
    document.documentElement.classList.add('light')
    document.documentElement.classList.remove('dark')
    localStorage.setItem('theme', 'light')
  }, [isDarkMode])

  const toggleTheme = (): void => {
    setIsDarkMode(!isDarkMode)
  }

  const value = {
    isDarkMode,
    toggleTheme
  }

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  )
}

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme debe usarse dentro de ThemeProvider')
  }
  return context
}
