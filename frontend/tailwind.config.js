/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        beige: {
          50: '#FDFBF7',
          100: '#FAF7F0',
          200: '#F5F0E8',
          300: '#EDE5D8',
          400: '#E0D5C5',
          500: '#CFC0A8',
        },
        burgundy: {
          50: '#F9F0F2',
          100: '#F0D9DE',
          200: '#D9A0AC',
          300: '#C0616F',
          400: '#8B1A2A',
          500: '#6B1020',
          600: '#4A0A16',
          700: '#2E0610',
        },
        gold: {
          300: '#E8C97A',
          400: '#D4A843',
          500: '#B8860B',
          600: '#9A6F08',
        },
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
      },
      fontFamily: {
        serif: ['Cormorant Garamond', 'Georgia', 'serif'],
        reading: ['Crimson Pro', 'Georgia', 'serif'],
        sans: ['Inter', 'DM Sans', 'sans-serif'],
      },
      fontSize: {
        'reading-sm': ['15px', { lineHeight: '1.75' }],
        reading: ['17px', { lineHeight: '1.75' }],
        'reading-lg': ['19px', { lineHeight: '1.75' }],
        'reading-xl': ['21px', { lineHeight: '1.75' }],
      },
      maxWidth: {
        reader: '58ch',
      },
      boxShadow: {
        book: '0 2px 8px rgba(107,16,32,0.08), 0 8px 32px rgba(107,16,32,0.12)',
        'book-hover': '0 8px 24px rgba(107,16,32,0.16), 0 16px 48px rgba(107,16,32,0.18)',
        toolbar: '0 -1px 0 rgba(107,16,32,0.08), 0 -4px 24px rgba(0,0,0,0.06)',
      },
      keyframes: {
        pulseSoft: {
          '0%,100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.7', transform: 'scale(1.06)' },
        },
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(12px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        highlightPulse: {
          '0%': { backgroundColor: 'rgba(212,168,67,0.6)' },
          '100%': { backgroundColor: 'rgba(212,168,67,0.25)' },
        },
        pageTurn: {
          '0%': { opacity: '0', transform: 'translateX(16px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        walletPulse: {
          '0%,100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.15)' },
        },
      },
      animation: {
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
        'fade-in': 'fadeIn 300ms ease forwards',
        'slide-up': 'slideUp 300ms ease forwards',
        highlight: 'highlightPulse 0.4s ease',
        'page-turn': 'pageTurn 400ms cubic-bezier(0.4,0,0.2,1) forwards',
        'wallet-pulse': 'walletPulse 1s ease-in-out infinite',
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
