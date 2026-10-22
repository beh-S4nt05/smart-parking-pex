/**
 * Tokens de design do SmartParking — extraídos dos templates do Figma
 * (Home, Login, Mapa de Vagas, Painel Admin, Simulador QR/Sensores).
 * Qualquer re-skin futuro toca só este arquivo + as classes mapeadas.
 */

export const colors = {
  // marca — azul royal dos templates
  primary: "#2563EB",
  primaryDark: "#1D4ED8",
  primarySoft: "#EFF6FF",
  navy: "#0F172A",
  navySoft: "#1E293B",

  // neutros
  bg: "#F8FAFC",
  surface: "#FFFFFF",
  text: "#0F172A",
  textBody: "#475569",
  textMuted: "#64748B",
  textFaint: "#94A3B8",
  border: "#E2E8F0",

  // feedback
  success: "#059669",
  successSoft: "#ECFDF5",
  danger: "#DC2626",
  dangerSoft: "#FEF2F2",
  warning: "#D97706",
  warningSoft: "#FFFBEB",
  info: "#2563EB",
  accentPurple: "#4F46E5",

  // status de vaga (mapa do app e do simulador)
  vagaLivre: "#059669",
  vagaLivreBg: "#ECFDF5",
  vagaLivreBorder: "#6EE7B7",
  vagaOcupada: "#DC2626",
  vagaOcupadaBg: "#FEF2F2",
  vagaOcupadaBorder: "#FCA5A5",
  vagaReservada: "#2563EB", // código azul sobre borda âmbar, como no Figma
  vagaReservadaBg: "#FFFBEB",
  vagaReservadaBorder: "#FCD34D",
  vagaInativa: "#94A3B8",
  vagaInativaBg: "#F8FAFC",
  vagaInativaBorder: "#E2E8F0",
} as const;

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
