// SDK 58 + NativeWind v4.2 (sem Reanimated — animações usam só Animated do RN core)
// IMPORTANTE: NÃO adicione "react-native-reanimated/plugin" nem
// "react-native-worklets/plugin" aqui. O babel-preset-expo do SDK 58 detecta o
// react-native-worklets instalado e configura o plugin sozinho. Colocar na mão
// gera o erro clássico:
//   "Duplicate plugin/preset detected" /
//   "It was moved to react-native-worklets package"
module.exports = function (api) {
  api.cache(true);

  return {
    presets: [
      ["babel-preset-expo", { jsxImportSource: "nativewind" }],
      "nativewind/babel",
    ],
    // O alias "@/*" -> "./src/*" é resolvido pelo Metro pelo tsconfigPaths,
    // habilitado por padrão no SDK 58. Não é necessário um plugin Babel extra.
  };
};
