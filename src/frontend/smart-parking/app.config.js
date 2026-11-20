/**
 * EAS/Expo: injeta google-services.json como arquivo de ambiente privado.
 * Nunca versionar o arquivo Firebase. GOOGLE_SERVICES_JSON e um CAMINHO
 * disponibilizado pelo Expo EAS ou configurado localmente no terminal.
 */
module.exports = ({ config }) => ({
  ...config,
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
