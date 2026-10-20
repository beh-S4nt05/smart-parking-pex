import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { parkingApi } from "../services/api";
import type { MapaVagas, Vaga } from "../types/api";

interface Options {
  pollingMs?: number;
}

/**
 * Mapa de vagas de um estacionamento (andares + vagas), com "ao vivo" opcional.
 * Retorna também helpers de resumo por andar usados pelo Mapa e pelo Simulador.
 */
export function useMapaVagas(estacionamentoId?: string, { pollingMs = 0 }: Options = {}) {
  const [mapa, setMapa] = useState<MapaVagas | null>(null);
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
    if (!estacionamentoId) return;
    try {
      const dados = await parkingApi.mapaVagas(estacionamentoId);
      if (!mounted.current) return;
      setMapa(dados);
      setErro(null);
      setAtualizadoEm(Date.now());
    } catch {
      if (mounted.current) setErro("Não foi possível carregar o mapa de vagas.");
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, [estacionamentoId]);

  useEffect(() => {
    setLoading(true);
    refresh();
    if (pollingMs > 0) {
      const t = setInterval(refresh, pollingMs);
      return () => clearInterval(t);
    }
  }, [refresh, pollingMs]);

  const resumo = useMemo(() => {
    const contar = (lista: Vaga[]) => ({
      livres: lista.filter((v) => v.status === "livre").length,
      ocupadas: lista.filter((v) => v.status === "ocupada").length,
      reservadas: lista.filter((v) => v.status === "reservada").length,
      inativas: lista.filter((v) => v.status === "inativa").length,
      total: lista.length,
    });
    return {
      geral: mapa ? contar(mapa.vagas) : null,
      porAndar: (andarId?: string) =>
        contar(
          mapa
            ? mapa.vagas.filter((v) => !andarId || v.andar_id === andarId)
            : [],
        ),
    };
  }, [mapa]);

  return { mapa, setMapa, loading, erro, atualizadoEm, refresh, resumo };
}
