/**
 * EAS/Expo: injeta google-services.json como arquivo de ambiente privado.
 * Nunca versionar o arquivo Firebase. GOOGLE_SERVICES_JSON e um CAMINHO
 * disponibilizado pelo Expo EAS ou configurado localmente no terminal.
 */
const idProjetoEas = process.env.EXPO_EAS_PROJECT_ID?.trim();

module.exports = ({ config }) => ({
  ...config,
  // Um projeto Expo/EAS precisa ter o ID real para builds Android e iOS.
  // Permite configurar no ambiente da máquina/CI sem inventar um ID.
  extra: idProjetoEas
    ? {
        ...config.extra,
        eas: { ...config.extra?.eas, projectId: idProjetoEas },
      }
    : config.extra,
  // Cloudflare Pages serve arquivos estaticos, mas /shopping/[id] e dinamico.
  // No deploy gratuito, exportar UMA SPA para links diretos/reload. Em CI
  // e no fluxo normal, preservar o render static aprovado da V1.
  web: {
    ...config.web,
    ...(process.env.SMARTPARKING_WEB_SPA === "true"
      ? { output: "single" }
      : {}),
  },
  android: {
    ...config.android,
    ...(process.env.GOOGLE_SERVICES_JSON
      ? { googleServicesFile: process.env.GOOGLE_SERVICES_JSON }
      : {}),
  },
});
