import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#3B82F6',
        success: '#10B981',
        warning: '#F59E0B',
        danger: '#EF4444',
        background: '#0F172A',
      },
      boxShadow: {
        card: '0 10px 25px -5px rgba(15, 23, 42, 0.15)',
      },
    },
  },
  plugins: [],
};

export default config;
