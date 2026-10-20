/**
 * "REDE CREDENCIADA — Shoppings Parceiros": cards por shopping com dados da
 * API (andares, total de vagas, badge de disponíveis colorida como no Figma).
 * No web vira grade (4 colunas); no mobile, lista vertical.
 */
import { Pressable, Text, View, useWindowDimensions } from "react-native";
import { Card, Chip, Logo } from "./ui";
import type { Estacionamento } from "../types/api";

interface Props {
  shoppings: Estacionamento[];
  selecionadoId?: string | null;
  onPress: (est: Estacionamento) => void;
}

function tonePorDisponibilidade(est: Estacionamento): "verde" | "ambar" | "vermelho" {
  const pct =
    est.total_vagas > 0
      ? ((est.vagas_disponiveis_total ?? 0) / est.total_vagas) * 100
      : 0;
  if (pct >= 25) return "verde";
  if (pct >= 10) return "ambar";
  return "vermelho";
}

function bairroDe(endereco?: string | null): string {
  if (!endereco) return "Manaus, AM";
  const partes = endereco.split(" - ");
  const bairro = partes[partes.length - 1]?.split(",")[0]?.trim();
  return bairro ? `${bairro}, Manaus` : "Manaus, AM";
}

export default function ShoppingList({ shoppings, selecionadoId, onPress }: Props) {
  const { width } = useWindowDimensions();
  const colunas = width >= 1180 ? 4 : width >= 768 ? 2 : 1;

  return (
    <View
      style={
        colunas > 1
          ? {
              flexDirection: "row",
              flexWrap: "wrap",
              gap: 14,
            }
          : { gap: 12 }
      }
    >
      {shoppings.map((est) => {
        const selecionado = est.id === selecionadoId;
        const livres = est.vagas_disponiveis_total ?? 0;
        return (
          <View
            key={est.id}
            style={
              colunas > 1
                ? { width: `calc(${100 / colunas}% - ${14 * ((colunas - 1) / colunas)}px)` as unknown as import("react-native").DimensionValue }
                : undefined
            }
            className={colunas > 1 ? "min-w-[240px] flex-1" : "w-full"}
          >
            <Pressable onPress={() => onPress(est)}>
              <Card
                className="p-4"
                style={
                  selecionado
                    ? { borderColor: "#2563EB", borderWidth: 2, backgroundColor: "#EFF6FF" }
                    : undefined
                }
              >
                {colunas > 1 ? (
                  <View className="gap-3">
                    <View className="flex-row items-center justify-between">
                      <Logo size={40} />
                      <Chip
                        label={`${livres} livres`}
                        tone={tonePorDisponibilidade(est)}
                      />
                    </View>
                    <View>
                      <Text className="text-base font-bold text-slate-900">
                        {est.nome}
                      </Text>
                      <Text className="mt-0.5 text-[13px] text-slate-500">
                        {bairroDe(est.endereco)}
                      </Text>
                      <Text className="mt-0.5 text-xs text-slate-400">
                        {est.total_andares} andares · {est.total_vagas} vagas
                      </Text>
                    </View>
                  </View>
                ) : (
                  <View className="flex-row items-center gap-3">
                    <Logo size={40} />
                    <View className="flex-1">
                      <Text className="text-[15px] font-bold text-slate-900">
                        {est.nome}
                      </Text>
                      <Text className="mt-0.5 text-xs text-slate-500">
                        {bairroDe(est.endereco)}
                      </Text>
                      <Text className="mt-0.5 text-[11px] text-slate-400">
                        {est.total_andares} andares · {est.total_vagas} vagas
                      </Text>
                    </View>
                    <Chip
                      label={`${livres} livres`}
                      tone={tonePorDisponibilidade(est)}
                    />
                  </View>
                )}
              </Card>
            </Pressable>
          </View>
        );
      })}
    </View>
  );
}
