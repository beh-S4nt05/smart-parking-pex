/** Notificações da V1: toda autorização é confirmada na API FastAPI. */
import { api } from "./api";

export type TipoNotificacao =
  | "reserva_confirmada" | "reserva_cancelada" | "reserva_expirada"
  | "reserva_concluida" | "lembrete_reserva" | "vaga_disponivel"
  | "pagamento_confirmado" | "caixa_fechado" | "resumo_financeiro"
  | "painel_reserva_criada" | "painel_reserva_cancelada"
  | "painel_reserva_expirada" | "painel_reserva_concluida";

export interface NotificacaoV1 {
  id: string;
  tipo: TipoNotificacao;
  titulo: string;
  mensagem: string;
  estacionamento_id: string | null;
  destino: string | null;
  referencia_tipo: string | null;
  referencia_id: string | null;
  criada_em: string;
  lida_em: string | null;
  expira_em: string | null;
}
export interface PreferenciasNotificacaoV1 {
  push_ativo: boolean;
  reservas: boolean;
  lembretes: boolean;
  vagas: boolean;
  financeiro: boolean;
  resumo_diario: boolean;
  silencio_inicio: number;
  silencio_fim: number;
}
export interface DiagnosticoPushV1 {
  envio_habilitado: boolean;
  criptografia_configurada: boolean;
  dispositivos_ativos: number;
  pronto: boolean;
  motivos: string[];
}

export interface AcompanhamentoV1 {
  id: string;
  estacionamento_id: string;
  andar_id: string | null;
  tipo_vaga: string | null;
  ativo: boolean;
}

export const notificacoesApi = {
  async diagnosticoPush() {
    const { data } = await api.get<DiagnosticoPushV1>("/api/notificacoes/push/status");
    return data;
  },
  async listar(filtro: "todas" | "nao_lidas" = "todas", offset = 0) {
    const { data } = await api.get<NotificacaoV1[]>("/api/notificacoes", {
      params: { minhas: filtro, offset, limite: 30 },
    });
    return data;
  },
  async contador() {
    const { data } = await api.get<{ nao_lidas: number }>("/api/notificacoes/contador");
    return data.nao_lidas;
  },
  async ler(id: string) {
    await api.patch("/api/notificacoes/" + encodeURIComponent(id) + "/ler");
  },
  async lerTodas() {
    await api.patch("/api/notificacoes/ler-todas");
  },
  async preferencias() {
    const { data } = await api.get<PreferenciasNotificacaoV1>("/api/notificacoes/preferencias");
    return data;
  },
  async salvarPreferencias(preferencias: PreferenciasNotificacaoV1) {
    await api.put("/api/notificacoes/preferencias", preferencias);
  },
  async acompanhamentos() {
    const { data } = await api.get<AcompanhamentoV1[]>("/api/notificacoes/acompanhamentos");
    return data;
  },
  async acompanhar(estacionamento_id: string, andar_id?: string, tipo_vaga = "comum") {
    const { data } = await api.post<{ id: string }>("/api/notificacoes/acompanhamentos", {
      estacionamento_id,
      andar_id: andar_id ?? null,
      tipo_vaga,
    });
    return data;
  },
  async pararAcompanhamento(id: string) {
    await api.delete("/api/notificacoes/acompanhamentos/" + encodeURIComponent(id));
  },
  async registrarDispositivo(token: string, plataforma: "android" | "ios") {
    const { data } = await api.post<{ id: string }>("/api/notificacoes/dispositivos", {
      token, plataforma,
    });
    return data.id;
  },
  async desvincularDispositivo(id: string) {
    await api.delete("/api/notificacoes/dispositivos/" + encodeURIComponent(id));
  },
};
