import { useCallback, useEffect, useRef, useState } from "react";
import { API_URL, parkingApi } from "../services/api";
import type { Estacionamento } from "../types/api";

interface Options {
  /** revalida a cada N ms (painéis "ao vivo"); 0 desliga */
  pollingMs?: number;
}

/**
 * Lista os estacionamentos com contagens reais do backend e, quando o
 * servidor não está acessível, mantém os últimos dados em cache local para
 * a Home nunca ficar vazia durante a demonstração.
 */
export function useEstacionamentos({ pollingMs = 0 }: Options = {}) {
  const [estacionamentos, setEstacionamentos] = useState<Estacionamento[]>([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [atualizadoEm, setAtualizadoEm] = useState<number>(Date.now());
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const refresh = useCallback(async () => {
    try {
      const dados = await parkingApi.listarEstacionamentos();
      if (!mounted.current) return;
      setEstacionamentos(dados);
      setErro(null);
      setAtualizadoEm(Date.now());
    } catch (e) {
      if (!mounted.current) return;
      setErro(
        estacionamentos.length > 0
          ? "Sem conexão com a API — mostrando a última leitura."
          : `API indisponível em ${API_URL} — verifique se o backend está nessa porta.`,
      );
    } finally {
      if (mounted.current) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    refresh();
    if (pollingMs > 0) {
      const t = setInterval(refresh, pollingMs);
      return () => clearInterval(t);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh, pollingMs]);

  return { estacionamentos, loading, erro, atualizadoEm, refresh };
}
