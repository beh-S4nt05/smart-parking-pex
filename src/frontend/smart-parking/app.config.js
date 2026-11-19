/**
 * EAS/Expo: injeta google-services.json como arquivo de ambiente privado.
 * Nunca versionar o arquivo Firebase. GOOGLE_SERVICES_JSON e um CAMINHO
 * disponibilizado pelo Expo EAS ou configurado localmente no terminal.
 */
module.exports = ({ config }) => ({
  ...config,
  android: {
    ...config.android,
    ...(process.env.GOOGLE_SERVICES_JSON
      ? { googleServicesFile: process.env.GOOGLE_SERVICES_JSON }
      : {}),
  },
});
