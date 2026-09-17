/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./App.{js,jsx,ts,tsx}",
    "./app/**/*.{js,jsx,ts,tsx}",
    "./src/**/*.{js,jsx,ts,tsx}", // Ajuste para as pastas onde seu código vive
  ],
  presets: [require("nativewind/preset")], // ⚠️ Obrigatório no NativeWind v4
  theme: {
    extend: {},
  },
  plugins: [],
};
