import { useCallback, useEffect, useRef, useState } from "react";
import { AppState, Platform } from "react-native";
import { parkingApi, apiErrorMessage } from "../services/api";
import type { Reserva } from "../types/api";

/** Revalida somente a lista pessoal, sem baixar todos os relatórios. */
export function useReservas(ativo: boolean, pollingMs = 1500) {
  const [reservas, setReservas] = useState<Reserva[]>([]);
  const [loading, setLoading] = useState(ativo);
  const [sincronizando, setSincronizando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [visivel, setVisivel] = useState(true);
  const emCurso = useRef(false);
  const ativoRef = useRef(ativo);
  const montado = useRef(true);
  const dadosRef = useRef<Reserva[]>([]);
  ativoRef.current = ativo;

  useEffect(() => {
    montado.current = true;
    return () => { montado.current = false; };
  }, []);

  useEffect(() => {
    if (Platform.OS === "web" && typeof document !== "undefined") {
      const verificar = () => setVisivel(document.visibilityState !== "hidden");
      verificar();
      document.addEventListener("visibilitychange", verificar);
      return () => document.removeEventListener("visibilitychange", verificar);
    }
    const sub = AppState.addEventListener("change", (estado) => {
      setVisivel(estado === "active");
    });
    return () => sub.remove();
  }, []);

  const refresh = useCallback(async () => {
    if (!ativoRef.current || emCurso.current) return;
    emCurso.current = true;
    if (dadosRef.current.length > 0) setSincronizando(true);
    try {
      const dados = await parkingApi.minhasReservas();
      if (!montado.current || !ativoRef.current) return;
      if (JSON.stringify(dadosRef.current) !== JSON.stringify(dados)) {
        dadosRef.current = dados;
        setReservas(dados);
      }
      setErro(null);
    } catch (e) {
      if (montado.current && ativoRef.current) {
        setErro(apiErrorMessage(e, "Não foi possível listar suas reservas."));
      }
    } finally {
      emCurso.current = false;
      if (montado.current) {
        setLoading(false);
        setSincronizando(false);
      }
    }
  }, []);

  useEffect(() => {
    if (!ativo) {
      dadosRef.current = [];
      setReservas([]);
      setErro(null);
      return;
    }
    if (!visivel) return;
    void refresh();
    if (pollingMs > 0) {
      const timer = setInterval(() => void refresh(), Math.max(1000, pollingMs));
      return () => clearInterval(timer);
    }
  }, [ativo, visivel, pollingMs, refresh]);

  const cancelar = useCallback(async (id: string) => {
    await parkingApi.cancelarReserva(id);
    await refresh();
  }, [refresh]);

  return { reservas, loading, sincronizando, erro, refresh, cancelar };
}
