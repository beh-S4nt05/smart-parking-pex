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
import { Platform } from "react-native";
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
// - Com .env: usa EXPO_PUBLIC_API_URL (o valor que mandar).
// - Web sem .env: auto-detecta o HOST atual na porta 8000 — abrir o preview no
//   celular ou noutro PC da rede já aponta para a máquina certa sozinha
//   (ex.: http://192.168.0.42:8000). OBS: o app NÃO tem env "DEFAULT_API_URL"
//   — se você precisa de outra porta (ex.: 8010), defina EXPO_PUBLIC_API_URL.
// - Nativo (Expo Go): localhost não existe no celular → configure o IP LAN.
const DEFAULT_API_URL = (() => {
  if (Platform.OS === "web" && typeof window !== "undefined") {
    const host = window.location?.hostname;
    if (host && host !== "localhost" && host !== "127.0.0.1") {
      return `http://${host}:8000`;
    }
  }
  return "http://localhost:8000";
})();

export const API_URL: string =
  (process.env.EXPO_PUBLIC_API_URL || DEFAULT_API_URL).replace(/\/+$/, "");

if (__DEV__) {
  // trilha de depuração: qual URL o app está usando (aparece no console do navegador/Metro)
  // eslint-disable-next-line no-console
  console.log(`[smart-parking] API_URL = ${API_URL}`);
}

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
    return `Não foi possível alcançar a API em ${API_URL} — confira se o backend está rodando nessa porta (src/backend/.env → PORT) e se o .env do app aponta para o mesmo endereço.`;
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
    // RF-13: avisa o servidor para revogar access+refresh ANTES de limpar o
    // armazenamento local; offline/401 não travam o logout do app.
    try {
      const refresh = await storage.getRefreshToken();
      await api.post(
        "/auth/logout",
        null,
        { params: refresh ? { refresh_token: refresh } : {}, timeout: 5000 },
      );
    } catch {
      /* melhor esforço — o clearTokens abaixo é o que fecha a sessão local */
    }
    await storage.clearTokens();
  },

  // ---- Conta (RF-15) ----
  async atualizarMe(payload: {
    nome?: string;
    telefone?: string;
    placa_veiculo?: string;
  }): Promise<Usuario> {
    const { data } = await api.put<Usuario>("/auth/me", payload);
    return data;
  },

  async trocarSenha(senha_atual: string, nova_senha: string): Promise<void> {
    await api.put("/auth/senha", { senha_atual, nova_senha });
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

  // ---- Cadastros do painel (admin global) ----
  async criarEstacionamento(payload: {
    nome: string;
    endereco?: string;
    total_andares: number;
    total_vagas: number;
    hora_abertura?: string;
    hora_fechamento?: string;
    taxa_hora: number;
    telefone?: string;
    latitude?: number;
    longitude?: number;
  }): Promise<Estacionamento> {
    const { data } = await api.post<Estacionamento>(
      "/api/admin/estacionamentos",
      payload,
    );
    return data;
  },

  async excluirEstacionamento(id: string): Promise<void> {
    await api.delete(`/api/admin/estacionamentos/${id}`);
  },

  async atualizarEstacionamento(
    id: string,
    payload: Partial<{
      nome: string;
      endereco: string;
      total_andares: number;
      total_vagas: number;
      hora_abertura: string;
      hora_fechamento: string;
      taxa_hora: number;
      telefone: string;
      latitude: number;
      longitude: number;
    }>,
  ): Promise<Estacionamento> {
    const { data } = await api.put<Estacionamento>(`/api/admin/estacionamentos/${id}`, payload);
    return data;
  },

  // RF-32: editar número/capacidade e excluir andar (a API já tinha DELETE, a UI não)
  async atualizarAndar(
    id: string,
    payload: { numero_andar?: number; capacidade?: number },
  ): Promise<{ id: string; numero_andar: number; capacidade: number }> {
    const { data } = await api.put(`/api/admin/andares/${id}`, payload);
    return data;
  },

  async excluirAndar(id: string): Promise<void> {
    await api.delete(`/api/admin/andares/${id}`);
  },

  // RF-33: CRUD fino de vaga
  async criarVaga(payload: {
    andar_id: string;
    codigo: string;
    tipo?: "comum" | "pcd" | "idoso" | "moto" | "eletrico";
  }): Promise<{ id: string }> {
    const { data } = await api.post("/api/admin/vagas", payload);
    return data;
  },

  async atualizarVaga(
    id: string,
    payload: {
      codigo?: string;
      tipo?: "comum" | "pcd" | "idoso" | "moto" | "eletrico";
      posicao_x?: number;
      posicao_y?: number;
    },
  ): Promise<{ id: string }> {
    const { data } = await api.put(`/api/admin/vagas/${id}`, payload);
    return data;
  },

  async excluirVaga(id: string): Promise<void> {
    await api.delete(`/api/admin/vagas/${id}`);
  },

  // RF-34: editar usuário (nome/tel/placa/role/vínculo/ativo) e reset de balcão (RF-14)
  async atualizarUsuario(
    id: string,
    payload: Partial<{
      nome: string;
      telefone: string;
      placa_veiculo: string;
      role: "usuario" | "gestor" | "financeiro" | "admin" | "publico";
      is_ativo: boolean;
      estacionamento_id: string | null;
    }>,
  ): Promise<Usuario> {
    const { data } = await api.put<Usuario>(`/api/admin/usuarios/${id}`, payload);
    return data;
  },

  async resetSenhaUsuario(id: string): Promise<{ senha_temporaria: string; aviso: string }> {
    const { data } = await api.post(`/api/admin/usuarios/${id}/reset-senha`);
    return data;
  },

  async criarAndar(payload: {
    estacionamento_id: string;
    numero_andar: number;
    capacidade: number;
  }): Promise<{ id: string; numero_andar: number; capacidade: number }> {
    const { data } = await api.post("/api/admin/andares", payload);
    return data;
  },

  async criarVagasEmLote(payload: {
    andar_id: string;
    quantidade: number;
    prefixo_codigo: string;
    tipo?: "comum" | "pcd" | "idoso" | "moto" | "eletrico";
  }): Promise<{ id: string }[]> {
    const { data } = await api.post("/api/admin/vagas/lote", payload);
    return data;
  },

  async criarUsuario(payload: {
    nome: string;
    email: string;
    senha: string;
    role: "usuario" | "gestor" | "financeiro" | "admin" | "publico";
    estacionamento_id?: string;
    telefone?: string;
  }): Promise<Usuario> {
    const { data } = await api.post<Usuario>("/api/admin/usuarios", payload);
    return data;
  },

  async alternarUsuario(id: string): Promise<Usuario> {
    const { data } = await api.patch<Usuario>(`/api/admin/usuarios/${id}/ativar-desativar`);
    return data;
  },

  // ---- Relatórios ----
  // Home pública: usa a variante de agregados (sem registros/valores) — o
  // fluxo detalhado exige papel de painel desde a auditoria de acesso de 20/10
  async fluxoHoje(estacionamentoId?: string) {
    const { data } = await api.get("/api/relatorios/fluxo/publico", {
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

  // ---- Marca 3 (SDD RF-52/54/55): relatórios do painel + exportação CSV ----
  async ocupacaoHistorica(
    periodo: "diario" | "semanal" | "mensal" = "semanal",
    estacionamentoId?: string
  ) {
    const { data } = await api.get("/api/relatorios/ocupacao-historica", {
      params: { periodo, ...(estacionamentoId ? { estacionamento_id: estacionamentoId } : {}) },
    });
    return data as {
      periodo: string;
      dias: number;
      dados_por_andar: Array<{
        andar_numero: number;
        estacionamento_id: string;
        vagas_ativas: number;
        ocupacao_por_hora: number[]; // 24 buckets locais (America/Manaus), %
      }>;
    };
  },

  async rotacao(
    periodo: "diario" | "semanal" | "mensal" = "diario",
    estacionamentoId?: string
  ) {
    const { data } = await api.get("/api/relatorios/rotacao", {
      params: { periodo, ...(estacionamentoId ? { estacionamento_id: estacionamentoId } : {}) },
    });
    return data as {
      total_entradas: number;
      tempo_medio_min: number;
      por_andar: Array<{
        andar_numero: number;
        estacionamento_id: string;
        entradas: number;
        vagas_ativas: number;
        giro: number;
        tempo_medio_min: number;
      }>;
    };
  },

  async financeiroResumo(
    periodo: "diario" | "semanal" | "mensal" = "diario",
    estacionamentoId?: string
  ) {
    const { data } = await api.get("/api/admin/financeiro/resumo", {
      params: { periodo, ...(estacionamentoId ? { estacionamento_id: estacionamentoId } : {}) },
    });
    return data as {
      faturamento_total: number;
      ticket_medio: number;
      total_pagamentos: number;
      pagamentos_pix: number;
      pagamentos_cartao: number;
      pagamentos_dinheiro: number;
      valor_pix: number;
      valor_cartao: number;
      valor_dinheiro: number;
      faturamento_por_dia: Array<{ data: string; valor: number }>;
      faturamento_por_tipo_vaga: Array<{ tipo_vaga: string; valor: number }>;
    };
  },

  /**
   * RF-55: baixa CSV pelo navegador (blob + <a download>). Em nativo o
   * `document` não existe → devolve false e a tela orienta o painel web.
   */
  async baixarCsv(
    tipo: "fluxo" | "financeiro",
    periodo: string,
    estacionamentoId?: string
  ): Promise<boolean> {
    const { data } = await api.get(`/api/relatorios/${tipo}/csv`, {
      params: { periodo, ...(estacionamentoId ? { estacionamento_id: estacionamentoId } : {}) },
      responseType: "blob",
    });
    if (typeof document === "undefined") return false;
    const url = URL.createObjectURL(data as unknown as Blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `relatorio_${tipo}_${periodo}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
    return true;
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
