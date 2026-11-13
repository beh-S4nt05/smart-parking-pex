/** Limpeza dos caches de shoppings no logout — sem importar hooks/contexto.

 * Fica separado para evitar ciclo `AuthContext → useEstacionamentos →
 * useAuth → AuthContext`. As chaves vivem em `cacheChaves.ts` (módulo puro).
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import { CHAVE_LEGADO, PREFIXO_CACHE } from "./cacheChaves";

/** Remove TODOS os caches de vitrine (chamado no logout). */
export async function limparCacheEstacionamentos(): Promise<void> {
  try {
    const chaves = await AsyncStorage.getAllKeys();
    const alvo = chaves.filter(
      (k) => k.startsWith(PREFIXO_CACHE) || k === CHAVE_LEGADO,
    );
    if (alvo.length) await AsyncStorage.multiRemove(alvo);
  } catch {
    // Cache não é credencial: falha aqui não pode travar o logout.
  }
}
