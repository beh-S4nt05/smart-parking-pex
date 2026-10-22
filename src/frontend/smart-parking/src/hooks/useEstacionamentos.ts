import { useCallback, useEffect, useRef, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";

const CHAVE_CACHE = "sp:cache:estacionamentos";
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
  const atualizadoRef = useRef(0);

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
      atualizadoRef.current = Date.now();
      // RF-06: grava a última boa leitura PERSISTIDA — sobrevive a restart
      AsyncStorage.setItem(CHAVE_CACHE, JSON.stringify({ ts: Date.now(), dados })).catch(() => {});
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

  // RF-06: boot lê o cache persistido imediatamente — a Home nunca abre vazia
  // se já houve uma leitura anterior, mesmo sem rede.
  useEffect(() => {
    (async () => {
      try {
        const bruto = await AsyncStorage.getItem(CHAVE_CACHE);
        if (!bruto || !mounted.current) return;
        const { ts, dados } = JSON.parse(bruto) as { ts: number; dados: Estacionamento[] };
        setEstacionamentos((atual) => (atual.length > 0 ? atual : dados));
        if (atualizadoRef.current === 0) {
          atualizadoRef.current = ts;
          setAtualizadoEm(ts);
        }
      } catch {
        /* cache corrompido — a próxima leitura da API sobrescreve */
      }
    })();
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
