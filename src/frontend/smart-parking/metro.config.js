const { getDefaultConfig } = require("expo/metro-config");
const { withNativeWind } = require("nativewind/metro");

// 1. Primeiro, pegamos a configuração padrão do Expo
const config = getDefaultConfig(__dirname);

// 2. Depois, aplicamos o NativeWind a essa configuração
module.exports = withNativeWind(config, {
  input: "./assets/Styles/global.css", // Certifique-se de que este arquivo existe!
});
