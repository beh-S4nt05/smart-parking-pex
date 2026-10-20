/**
 * Painel "STATUS DO ESTACIONAMENTO" da Home — 4 tiles com dados reais:
 * disponíveis, ocupação %, tempo médio (relatório de fluxo) e total.
 */
import { Text, View } from "react-native";
import { Card, StatTile, formatarMinutos } from "./ui";
import type { Estacionamento } from "../types/api";

interface Props {
  shopping: Estacionamento | null | undefined;
  tempoMedioMin: number | null;
}

export default function StatusPanel({ shopping, tempoMedioMin }: Props) {
  const total = shopping?.total_vagas ?? 0;
  const livres = shopping?.vagas_disponiveis_total ?? 0;
  const ocupacao = total > 0 ? Math.round(((total - livres) / total) * 100) : 0;

  return (
    <Card className="p-5 sm:p-6">
      <View className="mb-4 flex-row items-center gap-2">
        <View className="h-2 w-2 rounded-full bg-emerald-500" />
        <Text className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
          Status do estacionamento{shopping ? ` — ${shopping.nome}` : ""}
        </Text>
      </View>
      <View className="flex-row flex-wrap gap-3">
        <View className="min-w-[140px] flex-1">
          <StatTile rotulo="Vagas Disponíveis" valor={String(livres)} tone="verde" />
        </View>
        <View className="min-w-[140px] flex-1">
          <StatTile rotulo="Ocupação Atual" valor={`${ocupacao}%`} tone="azul" />
        </View>
        <View className="min-w-[140px] flex-1">
          <StatTile
            rotulo="Tempo Médio"
            valor={formatarMinutos(tempoMedioMin)}
            tone="roxo"
          />
        </View>
        <View className="min-w-[140px] flex-1">
          <StatTile rotulo="Total de Vagas" valor={String(total)} tone="neutro" />
        </View>
      </View>
    </Card>
  );
}
