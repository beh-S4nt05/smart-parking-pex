/**
 * Tokens de design do SmartParking — extraídos dos templates do Figma
 * (Home, Login, Mapa de Vagas, Painel Admin, Simulador QR/Sensores).
 * A tabela vive em src/styles/tokens.ts (fonte única de tokens).
 */
import { tokens } from "./styles/tokens";

export const colors = tokens.cor;

export type VagaTone = {
  text: string;
  bg: string;
  border: string;
};

export function vagaTone(status: string): VagaTone {
  switch (status) {
    case "livre":
      return { text: colors.vagaLivre, bg: colors.vagaLivreBg, border: colors.vagaLivreBorder };
    case "ocupada":
      return {
        text: colors.vagaOcupada,
        bg: colors.vagaOcupadaBg,
        border: colors.vagaOcupadaBorder,
      };
    case "reservada":
      return {
        text: colors.vagaReservada,
        bg: colors.vagaReservadaBg,
        border: colors.vagaReservadaBorder,
      };
    default:
      return {
        text: colors.vagaInativa,
        bg: colors.vagaInativaBg,
        border: colors.vagaInativaBorder,
      };
  }
}

/** Cor da barra de ocupação por andar: verde < 50 ≤ azul < 80 ≤ vermelho */
export function ocupacaoColor(percentual: number): string {
  if (percentual >= 80) return "#EF4444";
  if (percentual >= 50) return "#2563EB";
  return "#10B981";
}

/** Rótulos humanos dos status/tipos vindos da API */
export const VAGA_STATUS_LABEL: Record<string, string> = {
  livre: "Livre",
  ocupada: "Ocupada",
  reservada: "Reservada",
  inativa: "Inativa",
};

export const VAGA_TIPO_LABEL: Record<string, string> = {
  comum: "Comum",
  pcd: "PCD",
  idoso: "Idoso",
  moto: "Moto",
  eletrico: "Elétrico",
};

export const RESERVA_STATUS_LABEL: Record<string, string> = {
  confirmada: "Confirmada",
  cancelada: "Cancelada",
  concluida: "Concluída",
  expirada: "Expirada",
};

export const ORIGEM_LABEL: Record<string, string> = {
  sensor: "Sensor",
  simulador: "Simulador QR",
  app_motorista: "App motorista",
  manual: "Manual",
};
