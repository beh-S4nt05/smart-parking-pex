import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { parkingApi } from "../services/api";
import type { MapaVagas, Vaga } from "../types/api";

interface Options {
  pollingMs?: number;
}

function horaCache(ts: number): string {
  return new Date(ts).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

/** Mapa com atualização automática, cache offline e proteção contra respostas antigas. */
export function useMapaVagas(estacionamentoId?: string, { pollingMs = 0 }: Options = {}) {
  const [mapa, setMapa] = useState<MapaVagas | null>(null);
  const [loading, setLoading] = useState(Boolean(estacionamentoId));
  const [erro, setErro] = useState<string | null>(null);
  const [atualizadoEm, setAtualizadoEm] = useState<number>(Date.now());
  const mounted = useRef(true);
  const idAtual = useRef(estacionamentoId);
  const mapaRef = useRef<MapaVagas | null>(null);
  const atualizadoRef = useRef(0);
  const emCurso = useRef(new Set<string>());
  idAtual.current = estacionamentoId;

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    mapaRef.current = mapa;
  }, [mapa]);

  const refresh = useCallback(async () => {
    const idSolicitado = estacionamentoId;
    if (!idSolicitado) {
      if (mounted.current) setLoading(false);
      return;
    }
    if (emCurso.current.has(idSolicitado)) return;
    emCurso.current.add(idSolicitado);
    try {
      const dados = await parkingApi.mapaVagas(idSolicitado);
      if (!mounted.current || idAtual.current !== idSolicitado) return;
      mapaRef.current = dados;
      setMapa(dados);
      setErro(null);
      const agora = Date.now();
      atualizadoRef.current = agora;
      setAtualizadoEm(agora);
      AsyncStorage.setItem(
        `sp:cache:mapa:${idSolicitado}`,
        JSON.stringify({ ts: agora, dados }),
      ).catch(() => {});
    } catch {
      if (!mounted.current || idAtual.current !== idSolicitado) return;
      if (mapaRef.current) {
        setErro(`Sem conexão — última leitura ${horaCache(atualizadoRef.current)}.`);
        return;
      }
      try {
        const bruto = await AsyncStorage.getItem(`sp:cache:mapa:${idSolicitado}`);
        if (bruto && mounted.current && idAtual.current === idSolicitado) {
          const { ts, dados } = JSON.parse(bruto) as { ts: number; dados: MapaVagas };
          if (dados && Array.isArray(dados.vagas) && Number.isFinite(ts)) {
            mapaRef.current = dados;
            atualizadoRef.current = ts;
            setMapa(dados);
            setAtualizadoEm(ts);
            setErro(`Sem conexão — última leitura ${horaCache(ts)}.`);
            return;
          }
        }
      } catch {
        // Cache inválido: apresenta o erro de rede abaixo.
      }
      if (mounted.current && idAtual.current === idSolicitado) {
        setErro("Não foi possível carregar o mapa de vagas.");
      }
    } finally {
      emCurso.current.delete(idSolicitado);
      if (mounted.current && idAtual.current === idSolicitado) setLoading(false);
    }
  }, [estacionamentoId]);

  useEffect(() => {
    mapaRef.current = null;
    atualizadoRef.current = 0;
    setMapa(null);
    setErro(null);
    setLoading(Boolean(estacionamentoId));
    if (!estacionamentoId) return;

    void refresh();
    if (pollingMs > 0) {
      const timer = setInterval(() => void refresh(), pollingMs);
      return () => clearInterval(timer);
    }
  }, [estacionamentoId, refresh, pollingMs]);

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
        contar(mapa ? mapa.vagas.filter((v) => !andarId || v.andar_id === andarId) : []),
    };
  }, [mapa]);

  return { mapa, setMapa, loading, erro, atualizadoEm, refresh, resumo };
}
