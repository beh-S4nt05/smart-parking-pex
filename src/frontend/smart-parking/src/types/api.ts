/**
 * Tipos espelhando os schemas Pydantic do backend (FastAPI).
 * Manter em sincronia com `src/backend/models/schemas.py`.
 */

export type VagaStatus = "livre" | "ocupada" | "reservada" | "inativa";
export type VagaTipo = "comum" | "pcd" | "idoso" | "moto" | "eletrico";
export type ReservaStatus = "confirmada" | "cancelada" | "concluida";

export interface Usuario {
  id: string;
  nome: string;
  email: string;
  telefone?: string | null;
  placa_veiculo?: string | null;
  /** RF-47: autodeclaração PCD — vaga PCD só é atribuída a quem declara. */
  is_pcd?: boolean;
  is_ativo: boolean;
  role: "publico" | "usuario" | "financeiro" | "gestor" | "admin";
  estacionamento_id?: string | null;
  /** presente em /auth/me para quem tem estacionamento vinculado */
  estacionamento_nome?: string | null;
  criado_em?: string;
}

export interface SimSession {
  token: string;
  estacionamento_id: string;
  estacionamento_nome: string;
  andar_numero: number | null;
  criada_em: string;
  expira_em: string;
  expira_em_horas_restantes?: number;
  url?: string;
  qr_png_base64?: string | null;
}

export interface EventoVaga {
  id: string;
  vaga_codigo: string;
  vaga_status: VagaStatus;
  andar_numero: number | null;
  origem: "sensor" | "simulador" | "app_motorista" | "manual";
  evento: "entrada" | "saida" | "reserva";
  momento: string | null;
}

export interface OcupacaoAndar {
  andar_id: string;
  numero_andar: number;
  total_vagas: number;
  ocupadas: number;
  livres: number;
  percentual: number;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  user?: Usuario;
}

export interface Andar {
  id: string;
  estacionamento_id?: string;
  numero_andar: number;
  capacidade: number;
  criado_em?: string;
  vagas_livres?: number;
  vagas_ocupadas?: number;
}

export interface Estacionamento {
  id: string;
  nome: string;
  endereco?: string | null;
  total_andares: number;
  total_vagas: number;
  hora_abertura?: string | null;
  hora_fechamento?: string | null;
  taxa_hora?: number;
  telefone?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  criado_em?: string;
  andares: Andar[];
  vagas_disponiveis_total?: number;
}

export interface Vaga {
  id: string;
  andar_id: string;
  codigo: string;
  tipo: VagaTipo;
  posicao_x?: number | null;
  posicao_y?: number | null;
  status: VagaStatus;
  numero_andar?: number | null;
  ultima_atualizacao?: string | null;
}

export interface MapaVagas {
  estacionamento_id: string;
  estacionamento_nome: string;
  andares: Andar[];
  vagas: Vaga[];
}

export interface ProximaVaga {
  estacionamento_id: string;
  vaga: Vaga | null;
  andar_numero: number | null;
  mensagem: string;
  /** RF-47: presente quando a elegibilidade PCD mudou a atribuição. */
  aviso?: string | null;
}

export interface Reserva {
  id: string;
  vaga_id: string;
  usuario_id: string;
  horario_inicio: string;
  horario_fim: string;
  status: ReservaStatus;
  observacoes?: string | null;
  criado_em?: string;
  vaga?: Vaga | null;
}

export interface LoteVagasResultado {
  solicitadas: number;
  atualizadas: number;
  nao_encontradas: string[];
  vagas: Vaga[];
}

export interface DashboardAdmin {
  total_estacionamentos: number;
  total_usuarios_cadastrados: number;
  total_andares: number;
  total_vagas: number;
  ocupacao_atual: {
    livres: number;
    ocupadas: number;
    reservadas: number;
    taxa_ocupacao_percentual: number;
  };
  reservas_hoje: number;
}

export interface FluxoDia {
  data: string;
  entradas: number;
  saidas: number;
}

export interface RelatorioFluxo {
  periodo: string;
  estacionamento_id?: string | null;
  total_entradas: number;
  total_saidas: number;
  tempo_medio_permanencia_min: number;
  registros: Array<Record<string, unknown>>;
}

export interface RelatorioOcupacao {
  periodo: string;
  estacionamento_id?: string | null;
  taxa_ocupacao_media: number;
  total_vagas: number;
  vagas_ocupadas: number;
  dados_por_andar: Array<Record<string, unknown>>;
}

export interface ApiErrorBody {
  detail?: string | { msg?: string }[];
}
