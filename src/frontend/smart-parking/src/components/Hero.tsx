/**
 * Hero da Home — template "Home (MOBILE/WEB)" do Figma:
 * badge "Monitoramento em tempo real", título, seletor de shopping,
 * CTA e legenda de cores.
 *
 * A composição é 100% CSS (NativeWind), sem medir a largura em JS: o
 * pré-render estático e a hidratação entregam o mesmo arranjo em 320px,
 * 768px e 2560px. Lei de Jakob (padrão consistente), KISS (um único texto
 * de apoio) e Fitts (seletor e CTA adjacentes, ambos com alvo ≥ 44px).
 */
import { useEffect, useState } from "react";
import { Platform, Pressable, ScrollView, Text, View } from "react-native";
import { colors } from "../theme";
import { Botao, IconeChevron } from "./ui";
import ShoppingList from "./ShoppingList";
import type { Estacionamento } from "../types/api";

interface Props {
  shoppings: Estacionamento[];
  selecionadoId: string | null;
  onSelect: (id: string) => void;
  onBuscar: () => void;
}

export default function Hero({ shoppings, selecionadoId, onSelect, onBuscar }: Props) {
  const [listaAberta, setListaAberta] = useState(false);
  const selecionado =
    shoppings.find((s) => s.id === selecionadoId) ?? shoppings[0];
  const vazio = shoppings.length === 0;

  // Lista não pode ficar órfã se os dados sumirem durante uma atualização.
  useEffect(() => {
    if (vazio) setListaAberta(false);
  }, [vazio]);

  // Escape fecha a lista na Web; no nativo o botão permanece disponível.
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
    <View className="bg-blue-50/70 px-4 pb-6 pt-6 sm:px-6 sm:pb-10 sm:pt-12 3xl:pb-14 3xl:pt-16">
      <View className="mx-auto w-full max-w-[900px] items-center 3xl:max-w-[1100px]">
        <View className="mb-3 flex-row items-center gap-1.5 self-center rounded-full border border-blue-100 bg-white px-3.5 py-1.5 sm:mb-4">
          <View className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          <Text className="text-xs font-semibold text-blue-700">
            Monitoramento em tempo real
          </Text>
        </View>

        <Text className="text-balance text-center text-[26px] font-extrabold leading-[1.12] text-slate-900 sm:text-4xl lg:text-5xl 3xl:text-6xl">
          Encontre Vagas de Estacionamento!
        </Text>
        <Text className="mt-3 max-w-xl text-center text-sm leading-5 text-slate-600 sm:mt-4 sm:text-base sm:leading-6 3xl:max-w-2xl">
          Veja vagas livres por shopping e andar em Manaus, com atualização em tempo real.
        </Text>

        {/* seletor + CTA: mesma ordem em todas as larguras, sem sobreposição */}
        <View className="mt-5 flex w-full min-w-0 max-w-2xl flex-col gap-3 sm:mt-7 md:flex-row md:items-start md:gap-2.5 3xl:max-w-3xl">
          <View className="min-w-0 flex-1">
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={`Selecionar shopping: ${nomeSelecionado} — Manaus, AM`}
              accessibilityHint="Abre a lista de shoppings parceiros"
              accessibilityState={{ expanded: listaAberta, disabled: vazio }}
              aria-expanded={listaAberta}
              disabled={vazio}
              hitSlop={4}
              onPress={() => setListaAberta((v) => !v)}
              className={`min-h-12 flex-row items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-2.5 transition-colors hover:border-blue-300 active:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 motion-reduce:transition-none sm:px-4 sm:py-3 ${
                vazio ? "opacity-60" : ""
              }`}
            >
              <View className="h-2 w-2 shrink-0 rounded-full bg-blue-600" />
              {/* Nome e local em linhas separadas: o nome nunca é cortado em 320px. */}
              <View className="mx-2 min-w-0 flex-1">
                <Text numberOfLines={1} className="text-sm font-semibold text-slate-700">
                  {vazio ? "Carregando shoppings…" : nomeSelecionado}
                </Text>
                <Text className="mt-0.5 text-[11px] text-slate-500">Manaus, AM</Text>
              </View>
              <IconeChevron aberto={listaAberta} />
            </Pressable>

            {listaAberta && !vazio ? (
              <View
                nativeID="hero-lista-shoppings"
                accessibilityRole="list"
                accessibilityLabel="Lista de shoppings"
                className="mt-2 rounded-xl border border-slate-200 bg-white p-2"
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
            label="Ver Vagas Disponíveis"
            onPress={onBuscar}
            className="w-full rounded-xl md:w-auto"
          />
        </View>

        {/* legenda: agrupamento por proximidade, sem glifos de fonte */}
        <View className="mt-5 flex-row flex-wrap items-center justify-center gap-x-3 gap-y-1 sm:mt-6 sm:gap-x-5">
          {[
            { c: "#10B981", t: "Vaga livre" },
            { c: "#EF4444", t: "Vaga ocupada" },
            { c: colors.warning, t: "Poucas vagas" },
          ].map((i) => (
            <View key={i.t} className="flex-row items-center gap-1.5">
              <View className="h-2 w-2 rounded-full" style={{ backgroundColor: i.c }} />
              <Text className="text-[11px] text-slate-600 sm:text-[13px]">{i.t}</Text>
            </View>
          ))}
        </View>
      </View>
    </View>
  );
}
