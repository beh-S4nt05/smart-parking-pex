const fs = require("node:fs");
const path = require("node:path");
const {
  withAndroidManifest,
  withDangerousMod,
  withInfoPlist,
} = require("@expo/config-plugins");

const ARQUIVO_REDE = "smartparking_network_security.xml";

function ipv4Privado(host) {
  const partes = host.split(".");
  if (
    partes.length !== 4 ||
    partes.some((parte) => !/^(0|[1-9]\d{0,2})$/.test(parte))
  ) {
    return false;
  }
  const numeros = partes.map(Number);
  if (numeros.some((numero) => numero > 255)) return false;
  const [a, b] = numeros;
  return (
    a === 10 ||
    a === 127 ||
    (a === 172 && b >= 16 && b <= 31) ||
    (a === 192 && b === 168) ||
    (a === 169 && b === 254)
  );
}

function hostLocal(hostBruto) {
  const host = hostBruto.toLowerCase().replace(/\.$/, "");
  return (
    host === "localhost" ||
    host === "::1" ||
    ipv4Privado(host) ||
    // Nomes mDNS locais; não aceitamos domínios públicos parecidos.
    /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*\.(local|lan)$/.test(
      host,
    )
  );
}

/** Mantém a mesma prioridade do resolver nativo: MOBILE antes do global. */
function hostsLocaisDoAmbiente(env = process.env) {
  const valor =
    String(env.EXPO_PUBLIC_API_URL_MOBILE || "").trim() ||
    String(env.EXPO_PUBLIC_API_URL || "").trim();
  if (!valor) return [];

  let url;
  try {
    url = new URL(valor);
  } catch {
    throw new Error(
      `[withLocalNetwork] URL inválida: ${valor}. Informe http(s)://host:porta.`,
    );
  }
  if (url.protocol === "https:") return [];
  if (url.protocol !== "http:") {
    throw new Error(
      `[withLocalNetwork] Protocolo ${url.protocol} não permitido para a API; use HTTPS ou HTTP local.`,
    );
  }

  const host = url.hostname.replace(/^\[|\]$/g, "").toLowerCase();
  if (!hostLocal(host)) {
    throw new Error(
      `[withLocalNetwork] HTTP público (${host}) não é permitido. Use HTTPS para API pública ou um IP privado/localhost para desenvolvimento.`,
    );
  }
  return [host.replace(/\.$/, "")];
}

function xmlRedeLocal(hosts) {
  const dominios = hosts
    .map(
      (host) =>
        `    <domain includeSubdomains="false">${host}</domain>`,
    )
    .join("\n");
  return `<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
  <!-- Fechado por padrão: somente os hosts privados explícitos abaixo aceitam HTTP. -->
  <base-config cleartextTrafficPermitted="false" />
${
    dominios
      ? `  <domain-config cleartextTrafficPermitted="true">\n${dominios}\n  </domain-config>\n`
      : ""
  }</network-security-config>
`;
}

function withLocalNetwork(config) {
  // Expo Go não executa este plugin: nele o Metro/IP dinâmico continua igual.
  // Em prebuild/CNG, a exceção é materializada apenas para o host configurado.
  const hosts = hostsLocaisDoAmbiente();

  config = withInfoPlist(config, (modConfig) => {
    const plist = modConfig.modResults;
    const ats = { ...(plist.NSAppTransportSecurity || {}) };
    ats.NSAllowsArbitraryLoads = false;
    ats.NSAllowsLocalNetworking = hosts.length > 0;
    plist.NSAppTransportSecurity = ats;
    if (hosts.length > 0) {
      plist.NSLocalNetworkUsageDescription =
        plist.NSLocalNetworkUsageDescription ||
        "Permite conectar ao servidor Smart Parking na sua rede local durante o desenvolvimento.";
    }
    return modConfig;
  });

  config = withDangerousMod(config, [
    "android",
    async (modConfig) => {
      const diretorio = path.join(
        modConfig.modRequest.platformProjectRoot,
        "app",
        "src",
        "main",
        "res",
        "xml",
      );
      await fs.promises.mkdir(diretorio, { recursive: true });
      await fs.promises.writeFile(
        path.join(diretorio, ARQUIVO_REDE),
        xmlRedeLocal(hosts),
        "utf8",
      );
      return modConfig;
    },
  ]);

  return withAndroidManifest(config, (modConfig) => {
    const aplicacao = modConfig.modResults.manifest.application?.[0];
    if (!aplicacao) throw new Error("[withLocalNetwork] application ausente no AndroidManifest.");
    aplicacao.$["android:usesCleartextTraffic"] = "false";
    aplicacao.$["android:networkSecurityConfig"] = `@xml/${ARQUIVO_REDE.replace(/\.xml$/, "")}`;
    return modConfig;
  });
}

module.exports = withLocalNetwork;
module.exports.hostLocal = hostLocal;
module.exports.hostsLocaisDoAmbiente = hostsLocaisDoAmbiente;
module.exports.xmlRedeLocal = xmlRedeLocal;
