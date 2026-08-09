/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0f172a',
        panel: '#1e293b',
        border: 'rgba(255, 255, 255, 0.1)',
        primary: '#38bdf8',
        success: '#4ade80',
        danger: '#f87171',
        warning: '#fbbf24',
        textMuted: '#94a3b8'
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
