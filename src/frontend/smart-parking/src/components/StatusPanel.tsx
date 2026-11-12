/**
 * Painel "STATUS DO ESTACIONAMENTO" da Home — 4 indicadores com dados reais.
 * Lei da proximidade: rótulo e número sempre juntos num mesmo bloco.
 * Lei de Miller: quatro indicadores, nunca mais de sete por dobra.
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
    <Card className="p-5 sm:p-6 3xl:p-7">
      <View className="sp-secao mb-5 min-w-0">
        <Text className="text-[15px] font-extrabold text-slate-900">
          Status do estacionamento
        </Text>
        <Text className="mt-0.5 text-[12px] font-medium text-slate-600">
          {shopping ? shopping.nome : "Aguardando dados da API"} · atualizado em tempo real
        </Text>
      </View>
      <View className="flex-row flex-wrap gap-3 3xl:gap-4">
        <View className="min-w-0 basis-[140px] flex-grow">
          <StatTile rotulo="Vagas Disponíveis" valor={String(livres)} tone="verde" />
        </View>
        <View className="min-w-0 basis-[140px] flex-grow">
          <StatTile rotulo="Ocupação Atual" valor={`${ocupacao}%`} tone="azul" />
        </View>
        <View className="min-w-0 basis-[140px] flex-grow">
          <StatTile
            rotulo="Tempo Médio"
            valor={formatarMinutos(tempoMedioMin)}
            tone="roxo"
          />
        </View>
        <View className="min-w-0 basis-[140px] flex-grow">
          <StatTile rotulo="Total de Vagas" valor={String(total)} tone="neutro" />
        </View>
      </View>
    </Card>
  );
}
