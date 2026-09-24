/**
 * Instância pré-configurada do Axios para SmartParking
 * Compatível com Expo SDK 54 + TypeScript
 * Usa expo-secure-store para armazenar tokens de forma SEGURA (criptografada por hardware)
 *
 * Funcionalidades inclusas:
 * ✅ URL base da API configurável por ambiente
 * ✅ Armazena tokens JWT de forma segura com SecureStore
 * ✅ Adiciona token JWT automaticamente nas requisições autenticadas
 * ✅ Renova access_token automaticamente quando expirar, sem logout
 * ✅ Assina automaticamente todas as requisições de escrita com HMAC
 * ✅ Tratamento de erros padronizado
 */

import axios, {
  AxiosInstance,
  AxiosError,
  InternalAxiosRequestConfig,
  AxiosResponse,
} from "axios";
import * as SecureStore from "expo-secure-store";
import { addRequestSignerInterceptor } from "./requestSigner";

// Carrega URL base da API por ambiente
const API_URL: string =
  process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000";

// Tipagens para respostas da API
export interface ApiError {
  detail: string;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

// Chaves de armazenamento seguro
const KEY_ACCESS_TOKEN = "smartparking_access_token";
const KEY_REFRESH_TOKEN = "smartparking_refresh_token";

// Funções auxiliares para manipular SecureStore
async function saveAccessToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(KEY_ACCESS_TOKEN, token);
}

async function saveRefreshToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(KEY_REFRESH_TOKEN, token);
}

async function getAccessToken(): Promise<string | null> {
  return await SecureStore.getItemAsync(KEY_ACCESS_TOKEN);
}

async function getRefreshToken(): Promise<string | null> {
  return await SecureStore.getItemAsync(KEY_REFRESH_TOKEN);
}

async function clearTokens(): Promise<void> {
  await Promise.all([
    SecureStore.deleteItemAsync(KEY_ACCESS_TOKEN),
    SecureStore.deleteItemAsync(KEY_REFRESH_TOKEN),
  ]);
}

// Cria instância do Axios
const api: AxiosInstance = axios.create({
  baseURL: API_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// ======================================================================
// Interceptor 1: Adiciona token JWT automaticamente em requisições autenticadas
// ======================================================================
api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const isAuthRoute =
      config.url?.includes("/auth/login") ||
      config.url?.includes("/auth/refresh") ||
      config.url?.includes("/auth/registrar");
    if (!isAuthRoute) {
      const token = await getAccessToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error),
);

// ======================================================================
// Interceptor 2: Renovação automática de access_token quando expirar (401)
// ======================================================================
let isRefreshing: boolean = false;
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (
  error: AxiosError | null,
  token: string | null = null,
) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (
      error.response?.status !== 401 ||
      originalRequest._retry ||
      originalRequest.url?.includes("/auth/refresh")
    ) {
      if (originalRequest.url?.includes("/auth/refresh")) {
        await clearTokens();
        // Adicione navegação para tela de login aqui se necessário
      }
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      })
        .then((token) => {
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${token}`;
          }
          return api(originalRequest);
        })
        .catch((err) => Promise.reject(err));
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const refreshToken = await getRefreshToken();
      if (!refreshToken) {
        throw new Error("Sem refresh token");
      }

      const response = await api.post<Tokens>("/auth/refresh", {
        refresh_token: refreshToken,
      });

      const newAccessToken = response.data.access_token;
      await saveAccessToken(newAccessToken);

      processQueue(null, newAccessToken);

      if (originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
      }
      return api(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError as AxiosError, null);
      await clearTokens();
      // Redirecione para tela de login aqui
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

// ======================================================================
// Interceptor 3: Assinatura HMAC de requisições contra replicação
// ======================================================================
addRequestSignerInterceptor(api, {
  signWriteMethodsOnly: true,
});

// Funções auxiliares de autenticação exportadas para uso no app
export const auth = {
  /** Salva tokens após login/cadastro */
  async saveTokens(accessToken: string, refreshToken: string): Promise<void> {
    await Promise.all([
      saveAccessToken(accessToken),
      saveRefreshToken(refreshToken),
    ]);
  },
  /** Limpa tokens e desloga usuário */
  async logout(): Promise<void> {
    await clearTokens();
    // Navegue para tela de login aqui
  },
  /** Verifica se usuário já está logado */
  async isLoggedIn(): Promise<boolean> {
    const token = await getAccessToken();
    return !!token;
  },
};

export default api;
