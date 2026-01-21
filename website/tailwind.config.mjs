import typography from '@tailwindcss/typography';

export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: 'rgb(var(--color-ink) / <alpha-value>)',
        bone: 'rgb(var(--color-bone) / <alpha-value>)',
        rust: 'rgb(var(--color-rust) / <alpha-value>)',
        mint: 'rgb(var(--color-mint) / <alpha-value>)',
        sea: 'rgb(var(--color-sea) / <alpha-value>)',
        dusk: 'rgb(var(--color-dusk) / <alpha-value>)'
      },
      fontFamily: {
        display: ['"DM Serif Display"', 'serif'],
        body: ['"Space Grotesk"', 'sans-serif']
      },
      boxShadow: {
        glow: '0 0 0 3px rgba(255, 111, 76, 0.3), 0 10px 30px rgba(15, 22, 35, 0.3)'
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' }
        },
        sweep: {
          '0%': { transform: 'translateX(-20%)' },
          '100%': { transform: 'translateX(20%)' }
        }
      },
      animation: {
        float: 'float 6s ease-in-out infinite',
        sweep: 'sweep 18s ease-in-out infinite'
      },
      mediaQueries: {
        '(prefers-reduced-motion: no-preference)': { motion: 'no-preference' }
      }
    }
  },
  plugins: [typography]
};
