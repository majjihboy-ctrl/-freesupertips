/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        primary: 'var(--color-brand-green)',
        'primary-hover': 'var(--color-brand-green-hover)',
        'bg-base': 'var(--color-bg-base)',
        'bg-surface': 'var(--color-bg-surface)',
        'bg-surface-hover': 'var(--color-bg-surface-hover)',
        'brand-green': 'var(--color-brand-green)',
        'brand-green-hover': 'var(--color-brand-green-hover)',
        'brand-premium': 'var(--color-brand-premium)',
        'brand-danger': 'var(--color-brand-danger)',
      },
    },
  },
  plugins: [],
}