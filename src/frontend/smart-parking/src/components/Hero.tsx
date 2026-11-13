import { minW0Flex1, subtituloHero } from "../styles/recipes";
/**
 * Hero da Home — "Encontre Vagas de Estacionamento!" com busca em destaque.
 *
 * Composição 100% CSS (NativeWind), sem medir a largura em JS: pré-render e
 * hidratação entregam o mesmo arranjo de 320px a 2560px.
 *
 * Fitts: seletor e CTA grandes, adjacentes, dentro de um único cartão
 * elevado. Von Restorff: uma só ação cheia em toda a dobra. KISS/Tesler:
 * um único texto de apoio e sem lista de opções antes da busca.
 * Efeito estético-usabilidade: gradiente de marca, profundidade e tipografia
 * com hierarquia real — a primeira dobra agora se parece com um produto.
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

  useEffect(() => {
    if (vazio) setListaAberta(false);
  }, [vazio]);

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
    <View className="sp-hero bg-blue-50/70 px-4 pb-8 pt-8 sm:px-6 sm:pb-12 sm:pt-14 3xl:pb-16 3xl:pt-20">
      <View className="mx-auto w-full max-w-[980px] items-center 3xl:max-w-[1180px]">
        <View className="mb-4 flex-row items-center gap-2 self-center rounded-full border border-white/70 bg-white/90 px-4 py-2 shadow-sm sm:mb-6">
          <View className="h-2 w-2 rounded-full bg-emerald-500" />
          <Text className="text-xs font-bold tracking-wide text-blue-800">
            Monitoramento em tempo real
          </Text>
        </View>

        <Text className="text-balance text-center text-[30px] font-extrabold leading-[1.08] tracking-tight text-slate-900 sm:text-5xl lg:text-[56px] 3xl:text-[68px]">
          Encontre Vagas de{"\n"}Estacionamento!
        </Text>
        <Text className={subtituloHero}>
          Veja vagas livres por shopping e andar em Manaus, com atualização em tempo real.
        </Text>

        {/* Cartão de busca elevado: uma decisão por vez, sem elementos flutuantes. */}
        <View className="sp-busca mt-7 w-full min-w-0 max-w-2xl p-3 sm:mt-9 sm:p-4 3xl:max-w-3xl">
          <View className="mb-3 flex-row items-center gap-2 px-1">
            <View className="h-5 w-1 rounded-full bg-blue-600" />
            <Text className="text-[13px] font-bold uppercase tracking-wider text-slate-600">
              Onde você quer estacionar?
            </Text>
          </View>
          <View className="flex w-full min-w-0 flex-col gap-3 md:flex-row md:items-start md:gap-3">
            <View className={minW0Flex1}>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={`Selecionar shopping: ${nomeSelecionado} — Manaus, AM`}
                accessibilityHint="Abre a lista de shoppings parceiros"
                accessibilityState={{ expanded: listaAberta, disabled: vazio }}
                aria-expanded={listaAberta}
                disabled={vazio}
                hitSlop={4}
                onPress={() => setListaAberta((v) => !v)}
                className={`min-h-12 flex-row items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-2.5 web:transition-colors hover:border-blue-300 active:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 web:motion-reduce:transition-none sm:px-4 sm:py-3 ${
                  vazio ? "opacity-60" : ""
                }`}
              >
                <View className="h-2 w-2 shrink-0 rounded-full bg-blue-600" />
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
        </View>

        {/* Legenda agrupada: o significado das cores fica ao lado da decisão. */}
        <View className="mt-5 flex-row flex-wrap items-center justify-center gap-x-3 gap-y-1 sm:mt-6 sm:gap-x-6">
          {[
            { c: "#10B981", t: "Vaga livre" },
            { c: "#EF4444", t: "Vaga ocupada" },
            { c: colors.warning, t: "Poucas vagas" },
          ].map((i) => (
            <View key={i.t} className="flex-row items-center gap-1.5">
              <View className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: i.c }} />
              <Text className="text-[11px] font-medium text-slate-600 sm:text-[13px]">{i.t}</Text>
            </View>
          ))}
        </View>
      </View>
    </View>
  );
}
