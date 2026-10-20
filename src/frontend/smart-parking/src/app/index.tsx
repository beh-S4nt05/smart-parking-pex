/**
 * Home pública — template "Home (MOBILE/WEB)" do Figma, consumindo a API:
 * Hero com seletor de shopping, StatusPanel com números reais + tempo médio
 * do relatório de fluxo, e a rede credenciada de shoppings de Manaus.
 */
import { useCallback, useEffect, useState } from "react";
import {
  RefreshControl,
  ScrollView,
  Text,
  View,
  useWindowDimensions,
} from "react-native";
import { useRouter } from "expo-router";
import Header from "../components/Header";
import Hero from "../components/Hero";
import StatusPanel from "../components/StatusPanel";
import ShoppingList from "../components/ShoppingList";
import Footer from "../components/Footer";
import { useEstacionamentos } from "../hooks/useEstacionamentos";
import { parkingApi } from "../services/api";

export default function Index() {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const isWeb = width >= 1024;

  // "ao vivo": revalida a cada 20s enquanto a Home estiver aberta
  const { estacionamentos, loading, erro, refresh } = useEstacionamentos({
    pollingMs: 20000,
  });
  const [selecionadoId, setSelecionadoId] = useState<string | null>(null);
  const [tempoMedio, setTempoMedio] = useState<number | null>(null);

  useEffect(() => {
    if (!selecionadoId && estacionamentos.length > 0) {
      setSelecionadoId(estacionamentos[0].id);
    }
  }, [estacionamentos, selecionadoId]);

  const selecionado =
    estacionamentos.find((e) => e.id === selecionadoId) ?? estacionamentos[0] ?? null;

  // tempo médio de permanência (relatório de fluxo do dia)
  const carregarTempoMedio = useCallback(async (estId?: string) => {
    try {
      const f = await parkingApi.fluxoHoje(estId);
      setTempoMedio(f.tempo_medio_permanencia_min);
    } catch {
      setTempoMedio(null);
    }
  }, []);

  useEffect(() => {
    carregarTempoMedio(selecionado?.id);
  }, [selecionado?.id, carregarTempoMedio]);

  const abrirMapa = (id: string) => router.push(`/shopping/${id}` as never);

  return (
    <View className="flex-1 bg-slate-50">
      <Header rotaAtual="/" />
      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={false} onRefresh={refresh} tintColor="#2563EB" />}
      >
        <Hero
          shoppings={estacionamentos}
          selecionadoId={selecionado?.id ?? null}
          onSelect={setSelecionadoId}
          onBuscar={() => selecionado && abrirMapa(selecionado.id)}
        />

        <View className="mx-auto w-full max-w-7xl gap-8 px-4 py-8 sm:px-6">
          {erro ? (
            <View className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
              <Text className="text-[13px] font-medium text-amber-700">⚠️ {erro}</Text>
            </View>
          ) : null}

          <StatusPanel shopping={selecionado} tempoMedioMin={tempoMedio} />

          <View>
            <View className="mb-4 items-center gap-1">
              <Text className="text-[11px] font-bold uppercase tracking-wider text-blue-600">
                Rede credenciada
              </Text>
              <Text className={`text-center text-2xl font-extrabold text-slate-900 ${isWeb ? "text-3xl" : ""}`}>
                Shoppings Parceiros
              </Text>
              <Text className="text-sm text-slate-500">
                Escolha um shopping para ver o mapa de vagas em tempo real.
              </Text>
            </View>

            {!loading && estacionamentos.length === 0 ? (
              <View className="items-center rounded-2xl border border-slate-200 bg-white p-8">
                <Text className="text-base font-bold text-slate-900">
                  Nenhum estacionamento cadastrado ainda
                </Text>
                <Text className="mt-1 text-sm text-slate-500">
                  Rode o backend — o seed de demonstração popula os shoppings de
                  Manaus automaticamente.
                </Text>
              </View>
            ) : (
              <ShoppingList
                shoppings={estacionamentos}
                selecionadoId={selecionado?.id}
                onPress={(e) => abrirMapa(e.id)}
                variante="lista"
              />
            )}
          </View>
        </View>

        <Footer />
      </ScrollView>
    </View>
  );
}
