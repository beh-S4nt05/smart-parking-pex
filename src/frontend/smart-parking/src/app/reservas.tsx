/**
 * Minhas reservas — integração real: GET /api/reservas/minhas e
 * DELETE /api/reservas/{id} (a vaga volta a "livre" no mesmo instante).
 */
import { Alert, ScrollView, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useAuth } from "../hooks/useAuth";
import { useReservas } from "../hooks/useReservas";
import { apiErrorMessage } from "../services/api";
import Header from "../components/Header";
import {
  AnimarEntrada,
  BlocoCarregando,
  BlocoErro,
  BlocoVazio,
  Botao,
  Card,
  Chip,
} from "../components/ui";
import { RESERVA_STATUS_LABEL } from "../theme";

function formatarDataHora(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function Reservas() {
  const router = useRouter();
  const { isAuthenticated, loading: authLoading } = useAuth();
  const { reservas, loading, erro, refresh, cancelar } =
    useReservas(isAuthenticated && !authLoading);

  function pedirCancelamento(id: string, codigo: string) {
    Alert.alert(
      "Cancelar reserva",
      `Libera a vaga ${codigo} imediatamente.`,
      [
        { text: "Manter", style: "cancel" },
        {
          text: "Cancelar reserva",
          style: "destructive",
          onPress: async () => {
            try {
              await cancelar(id);
              Alert.alert(
                "Reserva cancelada",
                `A vaga ${codigo} voltou a ficar livre no mapa. ✅`,
              );
            } catch (e) {
              Alert.alert("Erro", apiErrorMessage(e));
            }
          },
        },
      ],
    );
  }

  return (
    <View className="flex-1 bg-slate-50">
      <Header rotaAtual="/" />
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 48 }}>
        <View className="mx-auto w-full max-w-3xl">
          <Text className="text-2xl font-extrabold text-slate-900">
            Minhas reservas
          </Text>
          <Text className="mt-1 text-sm text-slate-500">
            Acompanhe e gerencie as vagas que você garantiu.
          </Text>

          <View className="mt-6 gap-3">
            {authLoading || (!isAuthenticated && loading) ? (
              <BlocoCarregando />
            ) : !isAuthenticated ? (
              <BlocoVazio
                emoji="🔐"
                titulo="Entre para ver suas reservas"
                descricao="Faça login com sua conta de motorista para acompanhar suas vagas reservadas."
                acaoLabel="Fazer login"
                onAcao={() => router.push("/login")}
              />
            ) : loading ? (
              <BlocoCarregando />
            ) : erro && reservas.length === 0 ? (
              <BlocoErro
                titulo="Não foi possível carregar"
                descricao={erro}
                onAcao={refresh}
              />
            ) : reservas.length === 0 ? (
              <BlocoVazio
                emoji="🅿️"
                titulo="Nenhuma reserva ainda"
                descricao="Reserve uma vaga em segundos ao escolher um shopping — sem filas, sem procura."
                acaoLabel="Ver vagas disponíveis"
                onAcao={() => router.push("/explorar")}
              />
            ) : (
              reservas.map((r, idx) => {
                const codigo = r.vaga?.codigo ?? "—";
                const andar = r.vaga?.numero_andar;
                return (
                  <AnimarEntrada key={r.id} delay={idx * 45}>
                  <Card className="p-4">
                    <View className="flex-row items-center gap-4">
                      <View className="h-12 w-12 items-center justify-center rounded-xl bg-blue-600">
                        <Text className="text-[13px] font-extrabold text-white">
                          {codigo.split("-")[1] ?? codigo}
                        </Text>
                      </View>
                      <View className="flex-1">
                        <View className="flex-row items-center gap-2">
                          <Text className="text-base font-bold text-slate-900">
                            Vaga {codigo}
                            {andar != null ? ` · ${andar}º andar` : ""}
                          </Text>
                          <Chip
                            label={RESERVA_STATUS_LABEL[r.status] ?? r.status}
                            tone={
                              r.status === "confirmada"
                                ? "verde"
                                : r.status === "cancelada"
                                  ? "vermelho"
                                  : "neutro"
                            }
                          />
                        </View>
                        <Text className="mt-0.5 text-[13px] text-slate-500">
                          {formatarDataHora(r.horario_inicio)} →{" "}
                          {formatarDataHora(r.horario_fim)}
                          {r.observacoes ? ` · ${r.observacoes}` : ""}
                        </Text>
                      </View>
                    </View>

                    {r.status === "confirmada" ? (
                      <View className="mt-3 flex-row justify-end gap-2">
                        <Botao
                          label="Cancelar"
                          variant="contorno"
                          className="border-red-300 px-4 py-2"
                          onPress={() => pedirCancelamento(r.id, codigo)}
                        />
                      </View>
                    ) : null}
                  </Card>
                  </AnimarEntrada>
                );
              })
            )}
          </View>
        </View>
      </ScrollView>
    </View>
  );
}
