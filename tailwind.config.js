/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#22C55E',
        'primary-hover': '#16A34A',
        'bg-base': '#0B0F17',
        'bg-surface': '#141B29',
        'bg-surface-hover': '#1E2738',
        'brand-green': '#22C55E',
        'brand-green-hover': '#16A34A',
        'brand-premium': '#F5B731',
        'brand-danger': '#EF4444',
      },
    },
  },
  plugins: [],
}