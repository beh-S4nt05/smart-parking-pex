/** Chaves de cache da vitrine — módulo PURO (sem dependências RN/React).

 * Importável tanto pelo app quanto pelos testes Playwright (Node), sem
 * carregar AsyncStorage. A chave inclui a conta: assim um gestor nunca herda
 * a lista completa gravada por um admin no mesmo navegador.
 */
export const PREFIXO_CACHE = "sp:cache:estacionamentos:";
export const CHAVE_LEGADO = "sp:cache:estacionamentos";

export function chaveCacheVitrine(usuarioId?: string | null): string {
  return `${PREFIXO_CACHE}${usuarioId ?? "anonimo"}`;
}

export const CHAVE_CACHE_ANONIMO = chaveCacheVitrine(null);
