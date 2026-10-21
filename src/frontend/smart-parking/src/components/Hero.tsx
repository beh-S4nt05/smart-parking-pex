/**
 * Hero da Home — template "Home (MOBILE/WEB)" do Figma:
 * badge "Monitoramento em tempo real", título, seletor de shopping,
 * CTA "Ver Vagas Disponíveis →" e legenda de cores.
 */
import { useState } from "react";
import { Pressable, ScrollView, Text, View, useWindowDimensions } from "react-native";
import { colors } from "../theme";
import { Botao } from "./ui";
import ShoppingList from "./ShoppingList";
import type { Estacionamento } from "../types/api";

interface Props {
  shoppings: Estacionamento[];
  selecionadoId: string | null;
  onSelect: (id: string) => void;
  onBuscar: () => void;
}

export default function Hero({ shoppings, selecionadoId, onSelect, onBuscar }: Props) {
  const { width } = useWindowDimensions();
  const isWide = width >= 768;
  const [listaAberta, setListaAberta] = useState(false);
  const selecionado =
    shoppings.find((s) => s.id === selecionadoId) ?? shoppings[0];

  return (
    <View className="bg-blue-50/70 px-4 pb-10 pt-8 sm:px-6 sm:pt-12">
      <View className="mx-auto w-full items-center" style={{ maxWidth: 900 }}>
        <View className="mb-4 flex-row items-center gap-1.5 self-center rounded-full border border-blue-100 bg-white px-3.5 py-1.5">
          <View className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          <Text className="text-xs font-semibold text-blue-700">
            Monitoramento em tempo real
          </Text>
        </View>

        <Text
          className={`text-center font-extrabold leading-tight text-slate-900 ${
            isWide ? "text-5xl" : "text-3xl"
          }`}
        >
          Encontre Vagas de{"\n"}Estacionamento!
        </Text>
        <Text className="mt-4 max-w-xl text-center text-base leading-6 text-slate-500">
          {isWide
            ? "Saiba onde estacionar nos principais shoppings de Manaus em tempo real, com atualização automática por andar."
            : "Saiba onde estacionar nos principais shoppings de Manaus, em tempo real, com atualização por andar."}
        </Text>

        {/* seletor + CTA */}
        <View
          className={`mt-7 w-full max-w-2xl ${
            isWide ? "flex-row items-center gap-2.5" : "gap-3"
          }`}
        >
          {/* barra fechada = shopping atual; toque abre mini-lista de cards
              (mesmo ShoppingList da seção "Rede credenciada", variante lista) */}
          <View className="flex-1 relative">
            <Pressable
              accessibilityRole="button"
              onPress={() => shoppings.length > 0 && setListaAberta((v) => !v)}
              className={`flex-row items-center justify-between rounded-full bg-white px-4 ${
                isWide ? "py-3.5" : "rounded-2xl py-3"
              } border border-slate-200`}
            >
              <View className="h-2 w-2 rounded-full bg-blue-600" />
              <Text
                numberOfLines={1}
                className="mx-2 flex-1 text-sm font-semibold text-slate-700"
              >
                {shoppings.length === 0
                  ? "Carregando shoppings…"
                  : `${selecionado?.nome ?? ""} — Manaus, AM`}
              </Text>
              <Text className="text-base leading-5 text-blue-600">
                {listaAberta ? "˄" : "⌄"}
              </Text>
            </Pressable>

            {listaAberta && shoppings.length > 0 ? (
              <View
                className="absolute left-0 right-0 top-full z-20 mt-2 rounded-2xl border border-slate-200 bg-white p-2"
                style={{
                  elevation: 12,
                  shadowColor: "#0F172A",
                  shadowOpacity: 0.16,
                  shadowRadius: 20,
                  shadowOffset: { width: 0, height: 10 },
                }}
              >
                <ScrollView style={{ maxHeight: 360 }}>
                  <ShoppingList
                    shoppings={shoppings}
                    variante="lista"
                    selecionadoId={selecionado?.id ?? null}
                    onPress={(est) => {
                      onSelect(est.id);
                      setListaAberta(false);
                    }}
                  />
                </ScrollView>
              </View>
            ) : null}
          </View>

          <Botao
            label="Ver Vagas Disponíveis  →"
            onPress={onBuscar}
            className={isWide ? "" : "w-full"}
          />
        </View>

        {/* legenda */}
        <View className="mt-6 flex-row flex-wrap items-center justify-center gap-x-5 gap-y-1">
          {[
            { c: "#10B981", t: "Vaga livre" },
            { c: "#EF4444", t: "Vaga ocupada" },
            { c: colors.warning, t: "Poucas vagas" },
          ].map((i) => (
            <View key={i.t} className="flex-row items-center gap-1.5">
              <View className="h-2 w-2 rounded-full" style={{ backgroundColor: i.c }} />
              <Text className="text-[13px] text-slate-500">{i.t}</Text>
            </View>
          ))}
        </View>
      </View>
    </View>
  );
}
