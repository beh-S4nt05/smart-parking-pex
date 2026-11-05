import { useCallback, useEffect, useRef, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { API_URL, parkingApi } from "../services/api";
import type { Estacionamento } from "../types/api";

const CHAVE_CACHE = "sp:cache:estacionamentos";
const AVISO_STALE = "Sem conexão com a API — mostrando a última leitura.";

interface Options {
  /** Revalida a cada N ms; 0 desliga o polling. */
  pollingMs?: number;
}

/** Lista real com cache offline, recuperação automática e polling sem sobreposição. */
export function useEstacionamentos({ pollingMs = 0 }: Options = {}) {
  const [estacionamentos, setEstacionamentos] = useState<Estacionamento[]>([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [atualizadoEm, setAtualizadoEm] = useState<number>(Date.now());
  const mounted = useRef(true);
  const emCurso = useRef(false);
  const revalidou = useRef(false);
  const dadosRef = useRef<Estacionamento[]>([]);
  const atualizadoRef = useRef(0);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const refresh = useCallback(async () => {
    // Uma API lenta não pode acumular chamadas idênticas a cada intervalo.
    if (emCurso.current) return;
    emCurso.current = true;
    try {
      const dados = await parkingApi.listarEstacionamentos();
      if (!mounted.current) return;
      dadosRef.current = dados;
      revalidou.current = true;
      setEstacionamentos(dados);
      setErro(null);
      const agora = Date.now();
      setAtualizadoEm(agora);
      atualizadoRef.current = agora;
      AsyncStorage.setItem(CHAVE_CACHE, JSON.stringify({ ts: agora, dados })).catch(() => {});
    } catch {
      if (!mounted.current) return;
      // Usa o estado atual, não a closure vazia da primeira renderização.
      setErro(
        dadosRef.current.length > 0
          ? AVISO_STALE
          : `API indisponível em ${API_URL} — verifique se o backend está nessa porta.`,
      );
    } finally {
      emCurso.current = false;
      if (mounted.current) setLoading(false);
    }
  }, []);

  // O cache não sobrescreve uma resposta real que já chegou — nem mesmo uma
  // lista vazia válida. Se a rede falhou, os dados cacheados viram stale.
  useEffect(() => {
    (async () => {
      try {
        const bruto = await AsyncStorage.getItem(CHAVE_CACHE);
        if (!bruto || !mounted.current || revalidou.current) return;
        const { ts, dados } = JSON.parse(bruto) as { ts: number; dados: Estacionamento[] };
        if (!Array.isArray(dados) || !Number.isFinite(ts)) return;
        dadosRef.current = dados;
        setEstacionamentos(dados);
        setLoading(false);
        if (atualizadoRef.current === 0) {
          atualizadoRef.current = ts;
          setAtualizadoEm(ts);
        }
        setErro((atual) => (atual ? AVISO_STALE : atual));
      } catch {
        // Cache corrompido é ignorado; a próxima leitura válida o substitui.
      }
    })();
  }, []);

  useEffect(() => {
    void refresh();
    if (pollingMs > 0) {
      const timer = setInterval(() => void refresh(), pollingMs);
      return () => clearInterval(timer);
    }
  }, [refresh, pollingMs]);

  return { estacionamentos, loading, erro, atualizadoEm, refresh };
}
