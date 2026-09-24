import { useState, useCallback } from 'react';
import { api } from '../services/api';

export interface Vaga {
  id: string;
  codigo: string;
  status: 'livre' | 'ocupada' | 'reservada' | 'inativa';
  tipo_veiculo: string;
  andar_id?: string;
}

export function useVagas(estacionamentoId?: string) {
  const [vagas, setVagas] = useState<Vaga[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchVagas = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<Vaga[]>('/api/vagas', {
        params: { estacionamento_id: estacionamentoId },
      });
      setVagas(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao carregar lista de vagas.');
    } finally {
      setLoading(false);
    }
  }, [estacionamentoId]);

  const reservarVaga = async (vagaId: string) => {
    try {
      await api.post('/api/reservas', { vaga_id: vagaId });
      await fetchVagas(); // Atualiza a lista após efetuar a reserva
      return true;
    } catch (err: any) {
      throw new Error(err.response?.data?.detail || 'Erro ao efetuar reserva');
    }
  };

  return { vagas, loading, error, fetchVagas, reservarVaga };
}
