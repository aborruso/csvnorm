import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwind from '@astrojs/tailwind';
import { rehypeValidateAlt } from './src/lib/rehype-validate-alt.mjs';

const isProd = process.env.NODE_ENV === 'production';

export default defineConfig({
  site: isProd ? 'https://aborruso.github.io' : 'http://localhost:4321',
  base: isProd ? '/csvnorm' : '/',
  output: 'static',
  integrations: [
    react(),
    tailwind({
      config: {
        applyBaseStyles: false
      }
    })
  ],
  markdown: {
    rehypePlugins: [rehypeValidateAlt]
  }
});
