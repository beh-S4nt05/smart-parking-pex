// ======================================================================
// Resolução pura da URL base da API — separada de api.ts para ser
// testável em node sem runtime React Native (rod.13). api.ts injeta
// Platform/Constants/window e chama resolverApiURLBase().
//
// O erro clássico que derrubava só o celular: localhost no telefone é o
// próprio telefone. A web nunca sofria disso (usa o host do navegador) —
// daí o sintoma "web aceita os dados, mobile fica com frescura". Ordem:
//   1. EXPO_PUBLIC_API_URL_WEB (web) / EXPO_PUBLIC_API_URL_MOBILE (nativo)
//      — override por plataforma, scripts/dev-front.sh mantém o MOBILE
//      sincronizado com o IP LAN atual;
//   2. EXPO_PUBLIC_API_URL — override global (manda nas duas quando as
//      específicas estão ausentes);
//   3. auto-resolução: web = host do navegador; nativo = IP LAN que o
//      próprio Metro publica em Constants.expoConfig.hostUri. Host de
//      TÚNEL (u.expo.dev/… com `expo start --tunnel`) NÃO vira URL de API:
//      o túnel carrega só o bundle, a porta 8000 não é exposta — avisamos
//      em dev e caímos no próximo passo;
//   4. emulador Android → 10.0.2.2 (alias do host da máquina); iOS sim
//      compartilha a rede do Mac.
// ======================================================================

export type DepsResolucao = {
  ehWeb: boolean;
  envWeb?: string;
  envMobile?: string;
  envGlobal?: string;
  location?: { hostname: string; port: string; protocol: string } | null;
  hostUri?: string | null;
  ehAndroid?: boolean;
  warn?: (msg: string) => void;
};

const SEM_WARN = () => {};

/**
 * Sanitiza um valor manual de .env. `exp://` era a URL do QR do Expo Go,
 * nunca da API — convertemos para http:// (axios morreria no scheme) e
 * avisamos. Porta :8081 é o Metro servindo bundle, não a API (8000) — só
 * avisamos, o valor pode ser intencional (raro).
 */
export function limparUrlManual(bruto: string, chave: string, warn: (m: string) => void = SEM_WARN): string {
  let url = (bruto || "").trim().replace(/\/+$/, "");
  if (!url) return "";
  if (/^exp:\/\//i.test(url)) {
    url = "http://" + url.replace(/^exp:\/\//i, "");
    warn(`${chave}: exp:// é o deep-link do QR do Expo Go, não URL de API — converti para http:// (${url}). A API é a porta 8000.`);
  }
  if (/:8081(?::|$|\/)/.test(url) || url.endsWith(":8081")) {
    warn(`${chave} aponta para :8081, a porta do Metro (bundle). A API FastAPI roda na 8000 — se não foi engano, rode ./scripts/dev-front.sh que ele escreve a URL certa.`);
  }
  return url;
}

export function resolverApiURLBase(d: DepsResolucao): string {
  const warn = d.warn ?? SEM_WARN;

  const manual = limparUrlManual(
    (d.ehWeb ? d.envWeb : d.envMobile) || d.envGlobal || "",
    d.ehWeb ? "EXPO_PUBLIC_API_URL_WEB" : "EXPO_PUBLIC_API_URL_MOBILE",
    warn,
  );
  if (manual) return manual;

  if (d.ehWeb && d.location) {
    const { hostname, port, protocol } = d.location;
    if (port === "" || port === "80" || port === "443") {
      return `${protocol}//${hostname}`;
    }
    return `http://${hostname}:8000`;
  }

  // hostUri vem como "192.168.0.42:8081" ou "exp://192.168.0.42:8081"
  if (d.hostUri) {
    const host = d.hostUri.split("://").pop()!.split(":")[0].split("/")[0];
    if (host && host !== "localhost" && host !== "127.0.0.1" && host !== "[::1]") {
      if (/^\d+\.\d+\.\d+\.\d+$/.test(host) || /\.(local|lan)$/i.test(host)) {
        return `http://${host}:8000`;
      }
      warn(`hostUri do Metro="${host}" não é um IP LAN direto — parece túnel/hostname, e a porta 8000 da API NÃO é tunelada pelo Metro. Rode ./scripts/dev-front.sh (mesma rede Wi-Fi) ou defina EXPO_PUBLIC_API_URL_MOBILE com uma URL que o aparelho alcance.`);
    }
  }

  if (d.ehAndroid) return "http://10.0.2.2:8000";
  return "http://localhost:8000";
}
