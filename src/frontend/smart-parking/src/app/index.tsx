import { pagina, textoApoio, textoApoioCentro, tituloCard, tituloSecao } from "../styles/recipes";
/**
 * Home pública — template "Home (MOBILE/WEB)" do Figma, consumindo a API:
 * Hero com seletor de shopping, StatusPanel com números reais + tempo médio
 * do relatório de fluxo, e a rede credenciada de shoppings de Manaus.
 */
import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Platform,
  RefreshControl,
  ScrollView,
  Text,
  View,
} from "react-native";
import { useRouter } from "expo-router";
import Header from "../components/Header";
import Hero from "../components/Hero";
import MobileHome from "../components/MobileHome";
import StatusPanel from "../components/StatusPanel";
import ShoppingList from "../components/ShoppingList";
import Footer from "../components/Footer";
import { useEstacionamentos } from "../hooks/useEstacionamentos";
import { parkingApi } from "../services/api";

export default function Index() {
  const router = useRouter();

  const { estacionamentos, loading, atualizando, erro, refresh } = useEstacionamentos({
    pollingMs: 15000,
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
    void carregarTempoMedio(selecionado?.id);
    // Relatorio de fluxo e pesado; atualiza separadamente a cada 15 s.
    const timer = setInterval(() => void carregarTempoMedio(selecionado?.id), 15000);
    return () => clearInterval(timer);
  }, [selecionado?.id, carregarTempoMedio]);

  const abrirMapa = (id: string) => router.push(`/shopping/${id}` as never);

  if (Platform.OS !== "web") {
    return (
      <MobileHome
        shoppings={estacionamentos}
        selecionadoId={selecionado?.id ?? null}
        onSelect={setSelecionadoId}
        onBuscar={() => selecionado && abrirMapa(selecionado.id)}
        tempoMedio={tempoMedio}
        loading={loading}
        atualizando={loading || atualizando}
        erro={erro}
        refresh={refresh}
        onAbrirShopping={abrirMapa}
      />
    );
  }

  return (
    <View className={pagina}>
      <Header rotaAtual="/" />
      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={loading && estacionamentos.length > 0} onRefresh={refresh} tintColor="#2563EB" />}
      >
        <Hero
          shoppings={estacionamentos}
          selecionadoId={selecionado?.id ?? null}
          onSelect={setSelecionadoId}
          onBuscar={() => selecionado && abrirMapa(selecionado.id)}
          atualizando={loading || atualizando}
          erroAtualizacao={Boolean(erro)}
        />

        <View className="mx-auto w-full max-w-7xl gap-6 px-4 py-6 sm:gap-8 sm:px-6 sm:py-8 3xl:gap-10 3xl:px-8">
          {erro ? (
            <View className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
              <Text className="text-[13px] font-medium text-amber-700">Aviso: {erro}</Text>
            </View>
          ) : null}

          <StatusPanel shopping={selecionado} tempoMedioMin={tempoMedio} />

          <View>
            <View className="mb-6 items-center gap-1">
              <Text className="text-[11px] font-bold uppercase tracking-wider text-blue-600">
                Rede credenciada
              </Text>
              <Text className={tituloSecao}>
                Shoppings Parceiros
              </Text>
              <Text className={textoApoioCentro}>
                Escolha um shopping para ver o mapa de vagas em tempo real.
              </Text>
            </View>

            {loading && estacionamentos.length === 0 ? (
              <View accessible accessibilityLabel="Carregando estacionamentos"
                className="items-center justify-center gap-3 rounded-2xl border border-slate-200 bg-white p-10">
                <ActivityIndicator size="large" color="#2563EB" accessibilityLabel="Carregando estacionamentos" />
                <Text className="text-sm font-semibold text-slate-600">Carregando estacionamentos e vagas...</Text>
              </View>
            ) : estacionamentos.length === 0 ? (
              <View className="items-center rounded-2xl border border-slate-200 bg-white p-8">
                <Text className={tituloCard}>
                  Nenhum estacionamento cadastrado ainda
                </Text>
                <Text className={textoApoio}>
                  {erro ? "Não foi possível consultar os estacionamentos. Verifique a conexão e tente novamente." : "Nenhum shopping foi encontrado na rede credenciada."}
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
