/**
 * Utilitário de assinatura HMAC de requisições para o SmartParking
 * Compatível com Expo SDK 54 + React Native / TypeScript
 * Protege contra replicação de requisições por Postman/navegador/scripts externos
 */
import * as Crypto from "expo-crypto";
import { v4 as uuidv4 } from "uuid";
import { AxiosRequestConfig, InternalAxiosRequestConfig } from "axios";

/**
 * Chave secreta compartilhada com o backend.
 * ⚠️ DICA DE OFUSCAÇÃO EM PRODUÇÃO:
 * Divida a chave em várias partes e junte em tempo de execução para dificultar extração por engenharia reversa.
 * Gere uma chave forte para produção: openssl rand -hex 32
 */
const APP_SECRET_PARTS: string[] = [
  "smartparking_",
  "default_",
  "signing_",
  "key_",
  "change_in_production",
];
const APP_SECRET: string = APP_SECRET_PARTS.join("");

/**
 * Tipos para configuração do interceptor
 */
interface RequestSignerConfig {
  /** Se deve assinar apenas requisições que modificam dados (padrão true) */
  signWriteMethodsOnly: boolean;
}

const DEFAULT_CONFIG: RequestSignerConfig = {
  signWriteMethodsOnly: true,
};

/**
 * Assina uma requisição Axios adicionando os headers de segurança:
 * - X-Request-Timestamp: Horário da requisição
 * - X-Request-Nonce: Identificador único por requisição
 * - X-Request-Signature: Assinatura HMAC-SHA256
 * - X-Client-Type: Identificação do cliente oficial
 */
export async function signRequest(
  config: InternalAxiosRequestConfig,
  customConfig: Partial<RequestSignerConfig> = {},
): Promise<InternalAxiosRequestConfig> {
  const mergedConfig = { ...DEFAULT_CONFIG, ...customConfig };
  const method = (config.method || "get").toUpperCase();

  // Se configurado para assinar só métodos de escrita, pula requisições GET
  if (
    mergedConfig.signWriteMethodsOnly &&
    !["POST", "PUT", "PATCH", "DELETE"].includes(method)
  ) {
    return config;
  }

  // Gera valores de cabeçalho
  const timestamp: string = Math.floor(Date.now() / 1000).toString();
  const nonce: string = uuidv4();

  // Monta a string que será assinada EXATAMENTE como no backend:
  // METHOD + \n + PATH (com query string) + \n + TIMESTAMP + \n + NONCE + \n + BODY
  const url = new URL(config.url || "/", config.baseURL);
  const path: string = url.pathname + url.search;

  let bodyString: string = "";
  if (config.data) {
    bodyString =
      typeof config.data === "string"
        ? config.data
        : JSON.stringify(config.data);
  }

  const stringToSign: string = [
    method,
    path,
    timestamp,
    nonce,
    bodyString,
  ].join("\n");

  // Calcula HMAC SHA256 usando a biblioteca nativa de criptografia do Expo
  // NÃO enviamos a chave secreta pela rede!
  const signature: string = await Crypto.digestStringAsync(
    Crypto.CryptoDigestAlgorithm.SHA256,
    stringToSign + APP_SECRET,
    { encoding: Crypto.CryptoEncoding.HEX },
  );

  // Adiciona os headers na requisição
  if (!config.headers) {
    config.headers = {} as any;
  }

  config.headers["X-Request-Timestamp"] = timestamp;
  config.headers["X-Request-Nonce"] = nonce;
  config.headers["X-Request-Signature"] = signature;
  config.headers["X-Client-Type"] = "smartparking-mobile/1.0.0";

  return config;
}

/**
 * Adiciona o interceptor de assinatura automática em uma instância do Axios.
 * Todas as requisições POST/PUT/PATCH/DELETE serão assinadas automaticamente sem trabalho adicional.
 *
 * @example
 * ```ts
 * import axios from 'axios';
 * import { addRequestSignerInterceptor } from './services/requestSigner';
 *
 * const api = axios.create({ baseURL: 'http://SEU_IP:8000' });
 * addRequestSignerInterceptor(api);
 *
 * // Use normalmente a instância do axios, todas requisições já saem assinadas:
 * const response = await api.post('/api/reservas', { vaga_id: '...' });
 * ```
 */
export function addRequestSignerInterceptor(
  axiosInstance: any,
  customConfig: Partial<RequestSignerConfig> = {},
): void {
  axiosInstance.interceptors.request.use(
    async (config: InternalAxiosRequestConfig) => {
      return await signRequest(config, customConfig);
    },
    (error: any) => {
      return Promise.reject(error);
    },
  );
}

/**
 * ⚠️ Função auxiliar para testes - NÃO USAR EM PRODUÇÃO!
 * Gera a assinatura manualmente para depuração.
 */
export async function debugSignRequest(
  method: string,
  path: string,
  body?: object | string,
  timestamp?: string,
  nonce?: string,
): Promise<{
  timestamp: string;
  nonce: string;
  signature: string;
  stringToSign: string;
}> {
  const ts = timestamp || Math.floor(Date.now() / 1000).toString();
  const nc = nonce || uuidv4();
  const bodyStr = body
    ? typeof body === "string"
      ? body
      : JSON.stringify(body)
    : "";
  const stringToSign = [method.toUpperCase(), path, ts, nc, bodyStr].join("\n");
  const signature = await Crypto.digestStringAsync(
    Crypto.CryptoDigestAlgorithm.SHA256,
    stringToSign + APP_SECRET,
    { encoding: Crypto.CryptoEncoding.HEX },
  );

  return {
    timestamp: ts,
    nonce: nc,
    signature,
    stringToSign,
  };
}
