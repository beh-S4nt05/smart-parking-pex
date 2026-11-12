/**
 * "Lista de Shoppings" / "Reservar Vaga" — navegação do app: lista completa
 * dos shoppings credenciados com busca, ocupação real da API e atualização
 * automática. Clique abre o mapa de vagas do shopping.
 */
import { useMemo, useState } from "react";
import {
  RefreshControl,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { useRouter } from "expo-router";
import Header from "../components/Header";
import Footer from "../components/Footer";
import ShoppingList from "../components/ShoppingList";
import { Botao } from "../components/ui";
import { useEstacionamentos } from "../hooks/useEstacionamentos";
import { useAuth } from "../hooks/useAuth";
import { useAgora, desdeAte } from "../hooks/useAgora";

export default function Explorar() {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const { estacionamentos, loading, erro, atualizadoEm, refresh } =
    useEstacionamentos({ pollingMs: 15000 });
  const [busca, setBusca] = useState("");
  const agora = useAgora(5000);

  const filtrados = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    if (!termo) return estacionamentos;
    return estacionamentos.filter(
      (e) =>
        e.nome.toLowerCase().includes(termo) ||
        (e.endereco ?? "").toLowerCase().includes(termo),
    );
  }, [estacionamentos, busca]);

  return (
    <View className="flex-1 bg-slate-50">
      <Header rotaAtual="/explorar" />
      <ScrollView
        refreshControl={
          <RefreshControl refreshing={loading} onRefresh={refresh} tintColor="#2563EB" />
        }
      >
        <View className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6">
          <View className="mb-5 flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
            <View className="min-w-0 flex-1">
              <Text className="text-2xl font-extrabold text-slate-900 sm:text-3xl">
                Escolha um shopping
              </Text>
              <Text className="mt-1 text-sm text-slate-600">
                Veja vagas livres por local e andar. Atualizado {desdeAte(atualizadoEm, agora)}.
              </Text>
            </View>
            <View className="self-start rounded-full border border-emerald-200 bg-emerald-50 sm:self-auto">
              <View className="flex-row items-center gap-1.5 px-2.5 py-1">
                <View className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                <Text className="text-[11px] font-semibold text-emerald-700">
                  Ao vivo
                </Text>
              </View>
            </View>
          </View>

          <TextInput
            accessibilityLabel="Buscar shopping ou bairro"
            placeholder="Buscar por shopping ou bairro…"
            placeholderTextColor="#94A3B8"
            value={busca}
            onChangeText={setBusca}
            className="mb-5 rounded-xl border-2 border-slate-200 bg-white px-4 py-3 text-base text-slate-900 focus:border-blue-500"
          />

          {erro ? (
            <View className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
              <Text className="text-[13px] font-medium text-amber-700">Aviso: {erro}</Text>
            </View>
          ) : null}

          {filtrados.length === 0 && !loading ? (
            <View className="items-center rounded-2xl border border-slate-200 bg-white p-10">
              <Text className="mt-2 text-base font-bold text-slate-900">
                Nenhum shopping encontrado
              </Text>
              <Text className="mt-1 text-sm text-slate-600">
                Ajuste a busca ou verifique se a API está no ar.
              </Text>
            </View>
          ) : (
            <ShoppingList
              shoppings={filtrados}
              onPress={(e) => router.push(`/shopping/${e.id}` as never)}
            />
          )}

          {/* CTA de cadastro para reservar */}
          {!isAuthenticated ? <View className="mt-8 flex-col gap-4 rounded-2xl bg-slate-900 p-5 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:p-6">
            <View className="min-w-0 sm:flex-1">
              <Text className="text-lg font-bold text-white">
                Quer reservar antes de chegar?
              </Text>
              <Text className="mt-1 text-sm text-slate-300">
                Crie sua conta e reserve pelo app — é grátis.
              </Text>
            </View>
            <Botao
              label="Criar conta grátis"
              onPress={() => router.push("/cadastro")}
              className="w-full px-6 py-3 sm:w-auto"
            />
          </View> : null}
        </View>

        <Footer />
      </ScrollView>
    </View>
  );
}
