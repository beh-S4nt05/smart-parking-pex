import { useCallback, useEffect, useState } from "react";
import { parkingApi } from "../services/api";
import { apiErrorMessage } from "../services/api";
import type { Reserva } from "../types/api";

export function useReservas(ativo: boolean) {
  const [reservas, setReservas] = useState<Reserva[]>([]);
  const [loading, setLoading] = useState(ativo);
  const [erro, setErro] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const dados = await parkingApi.minhasReservas();
      setReservas(dados);
      setErro(null);
    } catch (e) {
      setErro(apiErrorMessage(e, "Não foi possível listar suas reservas."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (ativo) refresh();
  }, [ativo, refresh]);

  const cancelar = useCallback(async (id: string) => {
    await parkingApi.cancelarReserva(id);
    await refresh();
  }, [refresh]);

  return { reservas, loading, erro, refresh, cancelar };
}
