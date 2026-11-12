/** @type {import('tailwindcss').Config} */
// NativeWind v4 exige Tailwind 3.x (o react-native-css-interop 0.2.7 tem peer
// "tailwindcss": "~3"). NÃO subir para Tailwind 4 sem migrar para NativeWind v5.

module.exports = {
  // precisa cobrir app/ E src/ — se faltar caminho aqui, a classe simplesmente
  // não é gerada e o estilo "não aplica" sem erro nenhum.
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./src/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  darkMode: "class",
  theme: {
    // Breakpoints extras para monitor grande / TV (23"). O app usa a mesma
    // escala de 8px em todas as telas; em larguras extremas apenas o
    // conteúdo e a tipografia ganham mais espaço, sem mudar a composição.
    extend: {
      screens: {
        "3xl": "1920px",
        "4xl": "2560px",
      },
      maxWidth: {
        "8xl": "1440px",
        "9xl": "1680px",
      },
    },
  },
  plugins: [],
};
