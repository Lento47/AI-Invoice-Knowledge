/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        indigoBrand: '#3F51B5',
        crRed: '#CE1126',
        crBlue: '#002B7F',
        crGreen: '#3C8D0D'
      },
      boxShadow: {
        card: '0 10px 25px -20px rgba(0, 0, 0, 0.45)'
      },
      keyframes: {
        approve: {
          '0%': { transform: 'scale(0.9)', opacity: '0' },
          '60%': { transform: 'scale(1.05)', opacity: '1' },
          '100%': { transform: 'scale(1)', opacity: '1' }
        },
        reject: {
          '0%': { transform: 'translateX(0)' },
          '50%': { transform: 'translateX(-6px)' },
          '100%': { transform: 'translateX(0)' }
        }
      },
      animation: {
        approve: 'approve 320ms ease-out',
        reject: 'reject 260ms ease-out'
      }
    }
  },
  plugins: []
};
