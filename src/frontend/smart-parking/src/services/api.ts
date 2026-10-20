/**
 * Cliente HTTP do SmartParking — ponto único de integração com o backend.
 *
 * ✅ Exporta `api` como nomeado E default (o AppContext/hooks usam nomeado;
 *    o código antigo só tinha default e quebrava os imports)
 * ✅ Token JWT adicionado automaticamente
 * ✅ Renovação transparente do access_token em 401 (fila de requisições)
 * ✅ Assinatura HMAC de escrita (paridade com core/request_validator.py)
 * ✅ Funções tipadas por endpoint — telas não montam URL na mão
 */
import axios, {
  AxiosError,
  AxiosInstance,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";
import { storage } from "./storage";
import { addRequestSignerInterceptor } from "./requestSigner";
import type {
  DashboardAdmin,
  Estacionamento,
  EventoVaga,
  LoteVagasResultado,
  MapaVagas,
  OcupacaoAndar,
  ProximaVaga,
  Reserva,
  SimSession,
  Tokens,
  Usuario,
  Vaga,
  VagaStatus,
  VagaTipo,
} from "../types/api";

// URL base da API.
// - Dev web local: http://localhost:8000
// - Celular (Expo Go): EXPO_PUBLIC_API_URL=http://SEU_IP:8000
const DEFAULT_API_URL = __DEV__
  ? "http://localhost:8000"
  : "http://localhost:8000";

export const API_URL: string =
  process.env.EXPO_PUBLIC_API_URL || DEFAULT_API_URL;

const api: AxiosInstance = axios.create({
  baseURL: API_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// ======================================================================
// Interceptor 1: token JWT em requisições autenticadas
// ======================================================================
api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const isAuthRoute =
      config.url?.includes("/auth/login") ||
      config.url?.includes("/auth/refresh") ||
      config.url?.includes("/auth/registrar");
    if (!isAuthRoute) {
      const token = await storage.getAccessToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error),
);

// ======================================================================
// Interceptor 2: renovação automática do access_token em 401
// ======================================================================
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: AxiosError | null, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error);
    else prom.resolve(token);
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (
      error.response?.status !== 401 ||
      !originalRequest ||
      originalRequest._retry ||
      originalRequest.url?.includes("/auth/refresh") ||
      originalRequest.url?.includes("/auth/login")
    ) {
      if (originalRequest?.url?.includes("/auth/refresh")) {
        await storage.clearTokens();
      }
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return api(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const refreshToken = await storage.getRefreshToken();
      if (!refreshToken) throw new Error("Sem refresh token");

      const response = await api.post<Tokens>("/auth/refresh", {
        refresh_token: refreshToken,
      });

      const { access_token: newAccess, refresh_token: newRefresh, user } =
        response.data;
      await storage.setAccessToken(newAccess);
      if (newRefresh) await storage.setRefreshToken(newRefresh);
      if (user) await storage.setUserCache(JSON.stringify(user));

      processQueue(null, newAccess);
      originalRequest.headers.Authorization = `Bearer ${newAccess}`;
      return api(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError as AxiosError, null);
      await storage.clearTokens();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

// ======================================================================
// Interceptor 3: assinatura HMAC das escritas (anti-replicação)
// ======================================================================
addRequestSignerInterceptor(api, { signWriteMethodsOnly: true });

// ======================================================================
// Utilitários
// ======================================================================

/** Extrai uma mensagem legível do erro da API (detail string ou validação pydantic) */
export function apiErrorMessage(err: unknown, fallback = "Algo deu errado. Tente novamente."): string {
  const e = err as AxiosError<{ detail?: unknown }>;
  const detail = e?.response?.data?.detail;
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string };
    if (first?.msg) return humanizeValidationMessage(first.msg);
  }
  if (e?.code === "ERR_NETWORK" || !e?.response) {
    return "Não foi possível conectar ao servidor. Verifique sua internet ou se a API está no ar.";
  }
  return fallback;
}

function humanizeValidationMessage(msg: string): string {
  const map: Record<string, string> = {
    "value is not a valid email address": "E-mail inválido",
    "String should have at least 6 characters": "A senha precisa ter ao menos 6 caracteres",
    "String should have at least 8 characters": "A senha precisa ter ao menos 8 caracteres",
  };
  return map[msg] || msg;
}

// ======================================================================
// API tipada — um nome por chamada de rota, respostas tipadas
// ======================================================================
export const parkingApi = {
  // ---- Autenticação ----
  async login(credencial: string, senha: string): Promise<Tokens> {
    const { data } = await api.post<Tokens>("/auth/login", {
      email: credencial.trim(),
      senha,
    });
    await storage.setAccessToken(data.access_token);
    await storage.setRefreshToken(data.refresh_token);
    if (data.user) await storage.setUserCache(JSON.stringify(data.user));
    return data;
  },

  async registrar(payload: {
    nome: string;
    email: string;
    senha: string;
    telefone?: string;
    placa_veiculo?: string;
  }): Promise<Usuario> {
    const { data } = await api.post<Usuario>("/auth/registrar", payload);
    return data;
  },

  async me(): Promise<Usuario> {
    const { data } = await api.get<Usuario>("/auth/me");
    return data;
  },

  async logout(): Promise<void> {
    await storage.clearTokens();
  },

  // ---- Estacionamentos / vagas ----
  async listarEstacionamentos(): Promise<Estacionamento[]> {
    const { data } = await api.get<Estacionamento[]>("/api/estacionamentos");
    return data;
  },

  async obterEstacionamento(id: string): Promise<Estacionamento> {
    const { data } = await api.get<Estacionamento>(
      `/api/estacionamentos/${id}`,
    );
    return data;
  },

  async mapaVagas(id: string): Promise<MapaVagas> {
    const { data } = await api.get<MapaVagas>(
      `/api/estacionamentos/${id}/vagas`,
    );
    return data;
  },

  async proximaVaga(
    id: string,
    tipo?: VagaTipo,
  ): Promise<ProximaVaga> {
    const { data } = await api.get<ProximaVaga>(
      `/api/estacionamentos/${id}/proxima-vaga`,
      { params: tipo ? { tipo_vaga: tipo } : undefined },
    );
    return data;
  },

  async listarVagas(filtros?: {
    estacionamento_id?: string;
    andar_id?: string;
    status?: VagaStatus;
    tipo?: VagaTipo;
  }): Promise<Vaga[]> {
    const { data } = await api.get<Vaga[]>("/api/vagas", {
      params: filtros,
    });
    return data;
  },

  async atualizarStatusVaga(
    id: string,
    status: VagaStatus,
    origem?: "sensor" | "simulador" | "app_motorista" | "manual",
  ): Promise<Vaga> {
    const { data } = await api.patch<Vaga>(`/api/vagas/${id}/status`, {
      status,
      ...(origem ? { origem } : {}),
    });
    return data;
  },

  async atualizarStatusLote(
    vagaIds: string[],
    status: VagaStatus,
    origem?: "sensor" | "simulador" | "app_motorista" | "manual",
  ): Promise<LoteVagasResultado> {
    const { data } = await api.patch<LoteVagasResultado>(
      "/api/vagas/lote/status",
      { vaga_ids: vagaIds, status, ...(origem ? { origem } : {}) },
    );
    return data;
  },

  // ---- Reservas ----
  async criarReserva(payload: {
    vaga_id: string;
    horario_inicio: string;
    horario_fim: string;
    observacoes?: string;
  }): Promise<Reserva> {
    const { data } = await api.post<Reserva>("/api/reservas", payload);
    return data;
  },

  async minhasReservas(): Promise<Reserva[]> {
    const { data } = await api.get<Reserva[]>("/api/reservas/minhas");
    return data;
  },

  async cancelarReserva(id: string): Promise<Reserva> {
    const { data } = await api.delete<Reserva>(`/api/reservas/${id}`);
    return data;
  },

  // ---- Painel administrativo ----
  async dashboardAdmin(): Promise<DashboardAdmin> {
    const { data } = await api.get<DashboardAdmin>("/api/admin/dashboard");
    return data;
  },

  async dashboardGestor(): Promise<{
    estacionamento: { id: string; nome: string; endereco: string } | null;
    ocupacao: DashboardAdmin["ocupacao_atual"] & { total_vagas: number } | null;
    faturamento_hoje: number;
    ticket_medio_hoje: number;
    total_pagamentos_hoje: number;
    mensagem?: string;
  }> {
    const { data } = await api.get("/api/admin/gestor/dashboard");
    return data;
  },

  // ---- Sessões do simulador (painel → QR → celular) ----
  async criarSessaoSimulador(
    estacionamentoId: string,
    andarNumero?: number,
    expiraEmHoras: number = 12,
  ): Promise<SimSession> {
    const { data } = await api.post<SimSession>("/api/admin/simulador/sessoes", {
      estacionamento_id: estacionamentoId,
      andar_numero: andarNumero ?? null,
      expira_em_horas: expiraEmHoras,
    });
    return data;
  },

  async listarSessoesSimulador(): Promise<SimSession[]> {
    const { data } = await api.get<SimSession[]>("/api/admin/simulador/sessoes");
    return data;
  },

  async revogarSessaoSimulador(token: string): Promise<void> {
    await api.delete(`/api/admin/simulador/sessoes/${token}`);
  },

  async validarSessaoSimulador(token: string): Promise<SimSession> {
    const { data } = await api.get<SimSession>(
      `/api/admin/simulador/sessoes/${token}/validar`,
    );
    return data;
  },

  // ---- Feed do dashboard ----
  async listarEventos(
    estacionamentoId?: string,
    limite = 8,
  ): Promise<EventoVaga[]> {
    const { data } = await api.get<EventoVaga[]>("/api/admin/eventos", {
      params: {
        limite,
        ...(estacionamentoId ? { estacionamento_id: estacionamentoId } : {}),
      },
    });
    return data;
  },

  async ocupacaoPorAndar(estacionamentoId: string): Promise<OcupacaoAndar[]> {
    const { data } = await api.get<OcupacaoAndar[]>(
      `/api/admin/ocupacao-andares/${estacionamentoId}`,
    );
    return data;
  },

  // ---- Usuários (painel, admin) ----
  async listarUsuarios(): Promise<Usuario[]> {
    const { data } = await api.get<Usuario[]>("/api/admin/usuarios");
    return data;
  },

  async alternarUsuario(id: string): Promise<Usuario> {
    const { data } = await api.patch<Usuario>(`/api/admin/usuarios/${id}/ativar-desativar`);
    return data;
  },

  // ---- Relatórios ----
  async fluxoHoje(estacionamentoId?: string) {
    const { data } = await api.get("/api/relatorios/fluxo", {
      params: {
        periodo: "diario",
        ...(estacionamentoId ? { estacionamento_id: estacionamentoId } : {}),
      },
    });
    return data as {
      total_entradas: number;
      total_saidas: number;
      tempo_medio_permanencia_min: number;
      registros: Array<{
        id: string;
        entrada_em: string | null;
        saida_em: string | null;
        vaga_id?: string;
        valor_total?: number | null;
      }>;
    };
  },

  async relatorioFluxo(periodo: "diario" | "semanal" | "mensal", estacionamentoId?: string) {
    const { data } = await api.get("/api/relatorios/fluxo", {
      params: { periodo, ...(estacionamentoId ? { estacionamento_id: estacionamentoId } : {}) },
    });
    return data as {
      total_entradas: number;
      total_saidas: number;
      tempo_medio_permanencia_min: number;
      registros: Array<Record<string, unknown>>;
    };
  },

  async ocupacaoHoje(estacionamentoId?: string) {
    const { data } = await api.get("/api/relatorios/ocupacao", {
      params: {
        periodo: "diario",
        ...(estacionamentoId ? { estacionamento_id: estacionamentoId } : {}),
      },
    });
    return data as {
      taxa_ocupacao_media: number;
      total_vagas: number;
      vagas_ocupadas: number;
      dados_por_andar: Array<{
        andar: number;
        capacidade?: number;
        media_ocupacao?: number;
      }>;
    };
  },
};

export { api };
export default api;
