// SDK 57 + NativeWind v4.2 (sem Reanimated — animações usam só Animated do RN core)
// IMPORTANTE: NÃO adicione "react-native-reanimated/plugin" nem
// "react-native-worklets/plugin" aqui. O babel-preset-expo do SDK 57 detecta o
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
    plugins: [
      // faz o alias "@/*" -> "./src/*" do tsconfig funcionar em runtime (Metro).
      // Sem isto o TypeScript aceita o import, mas o bundler quebra.
      [
        "module-resolver",
        {
          root: ["./"],
          alias: { "@": "./src" },
          extensions: [".ts", ".tsx", ".js", ".jsx", ".json"],
        },
      ],
    ],
  };
};
