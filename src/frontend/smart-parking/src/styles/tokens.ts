/**
 * Fonte única dos tokens de design em TypeScript.
 *
 * `theme.ts` consome `tokens.cor` — não existe mais uma segunda tabela de
 * cores em JS. O espelho CSS fica em `assets/Styles/global.css` (`:root`),
 * porque o Metro/NativeWind aceita um único arquivo CSS de entrada e o CSS
 * não pode importar TypeScript. `scripts/check_design_tokens.cjs` falha se
 * as duas tabelas divergirem — a sincronia é verificada, não presumida.
 *
 * Lei da semelhança + Jakob: um mesmo valor de cor, raio e alvo em todo app.
 */
export const tokens = {
  cor: {
    // marca
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
    success: "#047857",
    successSoft: "#ECFDF5",
    danger: "#B91C1C",
    dangerSoft: "#FEF2F2",
    warning: "#D97706",
    warningSoft: "#FFFBEB",
    info: "#2563EB",
    accentPurple: "#4F46E5",
    // status de vaga
    vagaLivre: "#047857",
    vagaLivreBg: "#ECFDF5",
    vagaLivreBorder: "#6EE7B7",
    vagaOcupada: "#B91C1C",
    vagaOcupadaBg: "#FEF2F2",
    vagaOcupadaBorder: "#FCA5A5",
    vagaReservada: "#2563EB",
    vagaReservadaBg: "#FFFBEB",
    vagaReservadaBorder: "#FCD34D",
    vagaInativa: "#94A3B8",
    vagaInativaBg: "#F8FAFC",
    vagaInativaBorder: "#E2E8F0",
  },
  raio: { cartao: 20, campo: 14, botao: 14 },
  alvoMinimo: 44,
  transicaoMs: 150,
} as const;

export type Tokens = typeof tokens;
