/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Laranja da marca. #ee4d2d + texto branco reprova no contraste AA
        // (~3,65:1), entao superfices solidas com texto pequeno/branco usam o
        // `shopee-dark` (passa no AA); #ee4d2d fica nos acentos e titulos grandes.
        shopee: '#ee4d2d',
        'shopee-dark': '#cc3a17',
      },
    },
  },
  plugins: [],
}
