/**
 * Hero da Home — template "Home (MOBILE/WEB)" do Figma:
 * badge "Monitoramento em tempo real", título, seletor de shopping,
 * CTA "Ver Vagas Disponíveis →" e legenda de cores.
 */
import { useEffect, useState } from "react";
import { Platform, Pressable, Text, View } from "react-native";
import { useLarguraResponsiva } from "../hooks/useLarguraResponsiva";
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
  const width = useLarguraResponsiva();
  const isWide = width >= 640;
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
    <View className="bg-blue-50/70 px-4 pb-6 pt-6 sm:px-6 sm:pb-10 sm:pt-12">
      <View className="mx-auto w-full items-center" style={{ maxWidth: 900 }}>
        <View className="mb-3 flex-row items-center gap-1.5 self-center rounded-full border border-blue-100 bg-white px-3.5 py-1.5 sm:mb-5">
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
          Encontre Vagas de{"\n"}Estacionamento
        </Text>
        <Text className="mt-3 max-w-xl text-center text-sm leading-5 text-slate-600 sm:mt-4 sm:text-base sm:leading-6">
          Veja vagas livres por shopping e andar em Manaus, com atualização em tempo real.
        </Text>

        {/* seletor + CTA */}
        <View
          className={`mt-5 w-full min-w-0 max-w-2xl sm:mt-7 ${
            isWide ? "flex-row items-start gap-2.5" : "gap-3"
          }`}
        >
          {/* A lista expande o formulário e desloca o conteúdo seguinte. */}
          <View className="min-w-0 flex-1">
            <Text className="mb-2 text-sm font-semibold text-slate-700">Onde quer estacionar?</Text>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={`Selecionar shopping: ${nomeSelecionado} — Manaus, AM`}
              accessibilityHint="Abre a lista de shoppings parceiros"
              accessibilityState={{ expanded: listaAberta, disabled: vazio }}
              aria-expanded={listaAberta}
              disabled={vazio}
              hitSlop={4}
              onPress={() => setListaAberta((v) => !v)}
              className={`min-h-12 flex-row items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3 transition-colors hover:border-blue-300 active:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 motion-reduce:transition-none ${
                vazio ? "opacity-60" : ""
              }`}
            >
              <View className="h-2 w-2 rounded-full bg-blue-600" />
              <Text
                numberOfLines={1}
                className="mx-2 min-w-0 flex-1 text-sm font-semibold text-slate-700"
              >
                {vazio ? "Carregando shoppings…" : `${nomeSelecionado} — Manaus, AM`}
              </Text>
              <IconeChevron aberto={listaAberta} />
            </Pressable>

            {listaAberta && !vazio ? (
              <View
                nativeID="hero-lista-shoppings"
                accessibilityRole="list"
                accessibilityLabel="Lista de shoppings"
                className="mt-2 rounded-xl border border-slate-200 bg-white p-2"
              >
                <ShoppingList
                  shoppings={shoppings}
                  variante="lista"
                  selecionadoId={selecionado?.id ?? null}
                  onPress={(est) => {
                    onSelect(est.id);
                    setListaAberta(false);
                  }}
                />
              </View>
            ) : null}
          </View>

          <Botao
            label="Ver Vagas Disponíveis"
            onPress={onBuscar}
            className={isWide ? "mt-7 rounded-xl" : "w-full rounded-xl"}
          />
        </View>

      </View>
    </View>
  );
}
