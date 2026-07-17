/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#F6017C',
        'primary-hover': '#E5016C',
      },
    },
  },
  plugins: [],
}