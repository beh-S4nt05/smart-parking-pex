/**
 * Assinatura HMAC de requisições do SmartParking.
 *
 * ⚠️ Paridade com o backend (core/request_validator.py):
 *   X-Request-Signature = HMAC-SHA256(
 *     APP_SIGNING_SECRET,
 *     "METHOD\\nPATH?query\\nTIMESTAMP\\nNONCE\\nBODY"
 *   )  -> hex minúsculo
 *
 * O app calcula a chave em cima da string com crypto-js — o backend valida
 * com `hmac.new(secret, string, sha256)`. Qualquer divergência (ex.: usar
 * apenas SHA256(string + secret), como a versão antiga fazia) quebraria as
 * escritas em produção.
 */
import CryptoJS from "crypto-js";
import { InternalAxiosRequestConfig } from "axios";

/**
 * Chave compartilhada com o backend (APP_SIGNING_SECRET).
 * ⚠️ QA-101/22/10: antes era SÓ literal — seguir o conselho do
 * `src/backend/.env.example` ("troque a chave em produção") sem espelhar aqui
 * 403-ava TODAS as escritas quando `ENVIRONMENT=production`. Agora lê
 * `EXPO_PUBLIC_APP_SIGNING_SECRET` do .env do app (default mantém a demo).
 * Em produção real: ofuscar/injetar via CI e rotacionar.
 */
const APP_SECRET =
  process.env.EXPO_PUBLIC_APP_SIGNING_SECRET ||
  "smartparking_default_signing_key_change_in_production";

export interface RequestSignerConfig {
  /** Assinar apenas requisições que modificam dados (padrão true) */
  signWriteMethodsOnly: boolean;
}

const DEFAULT_CONFIG: RequestSignerConfig = {
  signWriteMethodsOnly: true,
};

function gerarNonce(): string {
  // 32 chars hex aleatórios — sem dependência externa
  return (
    CryptoJS.lib.WordArray.random(16).toString(CryptoJS.enc.Hex) +
    Date.now().toString(16)
  );
}

export function signRequest(
  config: InternalAxiosRequestConfig,
  customConfig: Partial<RequestSignerConfig> = {},
): InternalAxiosRequestConfig {
  const mergedConfig = { ...DEFAULT_CONFIG, ...customConfig };
  const method = (config.method || "get").toUpperCase();

  if (
    mergedConfig.signWriteMethodsOnly &&
    !["POST", "PUT", "PATCH", "DELETE"].includes(method)
  ) {
    return config;
  }

  const timestamp = Math.floor(Date.now() / 1000).toString();
  const nonce = gerarNonce();

  // path com query string, exatamente como o servidor vê (request.url.path)
  let path = config.url || "/";
  if (config.params && Object.keys(config.params).length > 0) {
    // axios serializa params internamente; replicamos o formato comum
    const search = new URLSearchParams(
      Object.entries(config.params as Record<string, unknown>)
        .filter(([, v]) => v !== undefined && v !== null)
        .map(([k, v]) => [k, String(v)]),
    ).toString();
    if (search) path += `?${search}`;
  } else if (path.includes("?")) {
    // mantém query já embutida na url
  }

  let bodyString = "";
  if (config.data) {
    bodyString =
      typeof config.data === "string"
        ? config.data
        : JSON.stringify(config.data);
  }

  const stringToSign = [method, path, timestamp, nonce, bodyString].join("\n");

  const signature = CryptoJS.HmacSHA256(stringToSign, APP_SECRET).toString(
    CryptoJS.enc.Hex,
  );

  if (!config.headers) {
    // axios v1 usa AxiosHeaders; apenas garante objeto para atribuir
    config.headers = {} as InternalAxiosRequestConfig["headers"];
  }

  config.headers["X-Request-Timestamp"] = timestamp;
  config.headers["X-Request-Nonce"] = nonce;
  config.headers["X-Request-Signature"] = signature;
  config.headers["X-Client-Type"] = "smartparking-mobile/1.0.0";

  return config;
}

/**
 * Instala o interceptor de assinatura em uma instância Axios.
 * Todas as escritas saem assinadas automaticamente.
 */
export function addRequestSignerInterceptor(
  axiosInstance: { interceptors: { request: { use: Function } } },
  customConfig: Partial<RequestSignerConfig> = {},
): void {
  axiosInstance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => signRequest(config, customConfig),
    (error: unknown) => Promise.reject(error),
  );
}
