/** @type {import('tailwindcss').Config} */
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // Colors are CSS variables so light and dark mode share one set of class names (see index.css).
      colors: {
        background: token('bg'),
        surface: token('surface'),
        subtle: token('subtle'),
        fg: token('fg'),
        muted: token('muted'),
        line: token('line'),
        accent: token('accent'),
        'accent-fg': token('accent-fg'),
        success: token('success'),
        danger: token('danger'),
        warning: token('warning'),
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
