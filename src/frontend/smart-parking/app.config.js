/**
 * EAS/Expo: injeta google-services.json como arquivo de ambiente privado.
 * Nunca versionar o arquivo Firebase. GOOGLE_SERVICES_JSON e um CAMINHO
 * disponibilizado pelo Expo EAS ou configurado localmente no terminal.
 */
const fs = require("node:fs");
const idProjetoEas = process.env.EXPO_EAS_PROJECT_ID?.trim();

function verificarFirebaseAndroid(arquivo, pacote) {
  if (process.env.EAS_BUILD !== "true" || process.env.EAS_BUILD_PLATFORM !== "android") {
    return;
  }
  if (!arquivo) {
    throw new Error("Configure GOOGLE_SERVICES_JSON no ambiente EAS do build Android para habilitar o FCM.");
  }

  let firebase;
  try {
    firebase = JSON.parse(fs.readFileSync(arquivo, "utf8"));
  } catch {
    throw new Error("GOOGLE_SERVICES_JSON deve apontar para um arquivo de configuração Firebase válido.");
  }
  if (!Array.isArray(firebase?.client) || !firebase.client.some(
    (cliente) => cliente?.client_info?.android_client_info?.package_name === pacote,
  )) {
    throw new Error(`GOOGLE_SERVICES_JSON não contém um cliente Firebase Android para ${pacote}.`);
  }
}

module.exports = ({ config }) => {
  verificarFirebaseAndroid(process.env.GOOGLE_SERVICES_JSON, config.android?.package);
  return {
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
  };
};
