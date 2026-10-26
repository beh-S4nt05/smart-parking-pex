/** Decisões puras do fluxo de autenticação, compartilhadas por app e testes. */

export const ROLES_PAINEL: readonly string[] = ["admin", "gestor", "financeiro"];

/** Somente resposta definitiva de autenticação/autorização encerra a sessão. */
export function erroRevogaSessao(erro: unknown): boolean {
  const status = (erro as { response?: { status?: number } } | null)?.response
    ?.status;
  return status === 401 || status === 403;
}

function destinoPadrao(role: string): string {
  return ROLES_PAINEL.includes(role) ? "/dashboard" : "/";
}

/**
 * Restringe `next` a uma rota interna adequada ao papel autenticado.
 * Evita open redirect, loop de login e retorno de motorista a painel/admin.
 */
export function destinoAposLogin(next: unknown, role: string): string {
  const candidato = Array.isArray(next) ? next[0] : next;
  if (typeof candidato !== "string") return destinoPadrao(role);

  const destino = candidato.trim();
  const caminho = destino.split(/[?#]/, 1)[0];
  const interno =
    destino.startsWith("/") &&
    !destino.startsWith("//") &&
    !destino.includes("://") &&
    !destino.includes("\\") &&
    !/[\r\n]/.test(destino) &&
    caminho !== "/login" &&
    caminho !== "/cadastro";
  if (!interno) return destinoPadrao(role);

  const papelTemPainel = ROLES_PAINEL.includes(role);
  if (caminho.startsWith("/dashboard") && !papelTemPainel) {
    return destinoPadrao(role);
  }
  if (
    (caminho.startsWith("/simulador") || caminho.startsWith("/simulador-qr")) &&
    role !== "admin"
  ) {
    return destinoPadrao(role);
  }
  return destino;
}
