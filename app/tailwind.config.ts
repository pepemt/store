import type { Config } from 'tailwindcss'

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f5f0f8',
          100: '#ebe1f1',
          200: '#d7c3e3',
          300: '#c3a5d5',
          400: '#af87c7',
          500: '#9b69b9',
          600: '#6e348d',
          700: '#5a2a72',
          800: '#461f56',
          900: '#32153b',
          950: '#1e0c23',
        },
      },
    },
  },
} satisfies Config
