/**
 * Hero da Home — template "Home (MOBILE/WEB)" do Figma:
 * badge "Monitoramento em tempo real", título, seletor de shopping,
 * CTA "Ver Vagas Disponíveis →" e legenda de cores.
 */
import { useEffect, useState } from "react";
import { Platform, Pressable, ScrollView, Text, View } from "react-native";
import { colors } from "../theme";
import { useLarguraResponsiva } from "../hooks/useLarguraResponsiva";
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
  const width = useLarguraResponsiva();
  const isWide = width >= 768;
  const [listaAberta, setListaAberta] = useState(false);
  const selecionado =
    shoppings.find((s) => s.id === selecionadoId) ?? shoppings[0];
  const vazio = shoppings.length === 0;

  // Lista não pode ficar órfã se os dados sumirem durante uma atualização.
  useEffect(() => {
    if (vazio) setListaAberta(false);
  }, [vazio]);

  // Escape fecha o seletor na Web; no nativo o backdrop e onRequestClose
  // já cobrem o gesto de voltar.
  useEffect(() => {
    if (!listaAberta || Platform.OS !== "web") return;
    const aoTeclar = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") setListaAberta(false);
    };
    document.addEventListener("keydown", aoTeclar);
    return () => document.removeEventListener("keydown", aoTeclar);
  }, [listaAberta]);

  const nomeSelecionado = selecionado?.nome ?? "Carregando shoppings…";

  return (
    <View className="relative bg-blue-50/70 px-4 pb-10 pt-8 sm:px-6 sm:pt-12">
      {/* backdrop: clique fora do seletor fecha a lista sem mover o conteúdo */}
      {listaAberta ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Fechar lista de shoppings"
          accessibilityHint="Fecha o seletor sem alterar o shopping escolhido"
          onPress={() => setListaAberta(false)}
          className="absolute inset-0 z-10"
        />
      ) : null}

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
          className={`relative z-20 mt-7 w-full max-w-2xl ${
            isWide ? "flex-row items-start gap-2.5" : "gap-3"
          }`}
        >
          {/* barra fechada = shopping atual; a mini-lista flutua SOBRE o
              conteúdo (absolute) em vez de empurrar cards para baixo. */}
          <View className="relative z-20 flex-1">
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={`Selecionar shopping: ${nomeSelecionado} — Manaus, AM`}
              accessibilityHint="Abre a lista de shoppings parceiros"
              accessibilityState={{ expanded: listaAberta, disabled: vazio }}
              aria-expanded={listaAberta}
              disabled={vazio}
              hitSlop={4}
              onPress={() => setListaAberta((v) => !v)}
              className={`flex-row items-center justify-between rounded-full bg-white px-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 motion-reduce:transition-none ${
                isWide ? "py-3.5" : "rounded-2xl py-3"
              } border border-slate-200 hover:border-blue-300 active:bg-blue-50 ${
                vazio ? "opacity-60" : ""
              }`}
            >
              <View className="h-2 w-2 rounded-full bg-blue-600" />
              <Text
                numberOfLines={1}
                className="mx-2 flex-1 text-sm font-semibold text-slate-700"
              >
                {vazio ? "Carregando shoppings…" : `${nomeSelecionado} — Manaus, AM`}
              </Text>
              <Text className="text-base leading-5 text-blue-600">
                {listaAberta ? "˄" : "⌄"}
              </Text>
            </Pressable>

            {listaAberta && !vazio ? (
              <View
                nativeID="hero-lista-shoppings"
                accessibilityRole="list"
                accessibilityLabel="Lista de shoppings"
                className="absolute left-0 right-0 top-full z-30 mt-2 rounded-2xl border border-slate-200 bg-white p-2"
                style={{
                  position: "absolute",
                  elevation: 12,
                  shadowColor: "#0F172A",
                  shadowOpacity: 0.16,
                  shadowRadius: 20,
                  shadowOffset: { width: 0, height: 10 },
                }}
              >
                <ScrollView style={{ maxHeight: 360 }} keyboardShouldPersistTaps="handled">
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
            className={isWide ? "relative z-0" : "relative z-0 w-full"}
          />
        </View>

        {/* legenda */}
        <View className="relative z-0 mt-6 flex-row flex-wrap items-center justify-center gap-x-5 gap-y-1">
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
