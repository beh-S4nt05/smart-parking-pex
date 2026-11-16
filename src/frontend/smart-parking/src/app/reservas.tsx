import { meta, minW0Flex1, pagina, textoApoio, tituloCardShopping } from "../styles/recipes";
/**
 * Minhas reservas — integração real: GET /api/reservas/minhas e
 * DELETE /api/reservas/{id} (a vaga volta a "livre" no mesmo instante).
 */
import { Alert, Platform, Pressable, RefreshControl, ScrollView, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../hooks/useAuth";
import { useReservas } from "../hooks/useReservas";
import { apiErrorMessage } from "../services/api";
import Header from "../components/Header";
import { MobileBottomNav, MobileScreenHeader } from "../components/MobileChrome";
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
                `A vaga ${codigo} voltou a ficar livre no mapa.`,
              );
            } catch (e) {
              Alert.alert("Erro", apiErrorMessage(e));
            }
          },
        },
      ],
    );
  }

  if (Platform.OS !== "web") {
    const ativas = reservas.filter((r) => r.status === "confirmada");
    const historico = reservas.filter((r) => r.status !== "confirmada");
    const cartaoReserva = (r: (typeof reservas)[number]) => {
      const codigo = r.vaga?.codigo ?? "—";
      const ativo = r.status === "confirmada";
      return (
        <View key={r.id} style={{ backgroundColor: "#FFFFFF", padding: 17, borderRadius: 19, marginBottom: 12 }}>
          <View style={{ flexDirection: "row", gap: 13, alignItems: "center" }}>
            <View style={{ width: 50, height: 50, borderRadius: 15, backgroundColor: ativo ? "#EAF1FF" : "#F1F5F9", alignItems: "center", justifyContent: "center" }}>
              <Ionicons name="car-sport-outline" size={26} color={ativo ? "#2563EB" : "#64748B"} />
            </View>
            <View style={{ flex: 1, minWidth: 0 }}>
              <Text style={{ fontSize: 16, fontWeight: "800", color: "#15233B" }}>Vaga {codigo}</Text>
              <Text style={{ color: "#64748B", fontSize: 12, marginTop: 3 }}>
                {r.vaga?.numero_andar != null ? `${r.vaga.numero_andar}º andar · ` : ""}{formatarDataHora(r.horario_inicio)}
              </Text>
            </View>
            <View style={{ borderRadius: 20, backgroundColor: ativo ? "#D1FAE5" : "#F1F5F9", paddingHorizontal: 10, paddingVertical: 6 }}>
              <Text style={{ color: ativo ? "#047857" : "#64748B", fontSize: 11, fontWeight: "800" }}>{RESERVA_STATUS_LABEL[r.status] ?? r.status}</Text>
            </View>
          </View>
          <View style={{ marginTop: 13, borderTopWidth: 1, borderColor: "#EDF2F7", paddingTop: 11 }}>
            <Text style={{ fontSize: 12, color: "#64748B" }}>Início: {formatarDataHora(r.horario_inicio)}</Text>
            <Text style={{ fontSize: 12, color: "#64748B", marginTop: 4 }}>Término: {formatarDataHora(r.horario_fim)}</Text>
            <Text style={{ fontSize: 12, color: "#475569", marginTop: 7, fontWeight: "700" }}>
              {r.veiculo ? `Veículo: ${r.veiculo.placa} · ${r.veiculo.categoria === "moto" ? "Moto" : "Carro"}` : "Veículo não informado (reserva anterior)"}
            </Text>
          </View>
          {ativo ? (
            <Pressable onPress={() => pedirCancelamento(r.id, codigo)} accessibilityRole="button" accessibilityLabel={`Cancelar reserva da vaga ${codigo}`} style={{ minHeight: 44, borderRadius: 12, backgroundColor: "#FFF1F2", alignItems: "center", justifyContent: "center", marginTop: 12 }}>
              <Text style={{ fontSize: 13, fontWeight: "800", color: "#BE123C" }}>Cancelar reserva</Text>
            </Pressable>
          ) : null}
        </View>
      );
    };
    return (
      <View style={{ flex: 1, backgroundColor: "#F3F7FD" }}>
        <MobileScreenHeader title="Minhas reservas" subtitle="Suas vagas e seu histórico" />
        <ScrollView
          style={{ flex: 1 }}
          contentContainerStyle={{ padding: 18, paddingBottom: 36 }}
          refreshControl={<RefreshControl refreshing={loading && !authLoading} onRefresh={refresh} tintColor="#2563EB" />}
        >
          {authLoading || loading ? (
            <BlocoCarregando />
          ) : !isAuthenticated ? (
            <BlocoVazio nomeIcone="lock-closed-outline" titulo="Entre para ver suas reservas" descricao="Acesse sua conta para acompanhar suas vagas." acaoLabel="Fazer login" onAcao={() => router.push("/login")} />
          ) : erro && reservas.length === 0 ? (
            <BlocoErro titulo="Não foi possível carregar" descricao={erro} onAcao={refresh} />
          ) : (
            <>
              <View style={{ backgroundColor: "#0F1E38", borderRadius: 21, padding: 20, marginBottom: 24, flexDirection: "row", alignItems: "center", gap: 15 }}>
                <View style={{ width: 54, height: 54, backgroundColor: "#1D3D66", borderRadius: 17, alignItems: "center", justifyContent: "center" }}>
                  <Ionicons name="ticket-outline" size={28} color="#6EE7B7" />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={{ color: "#FFFFFF", fontSize: 27, fontWeight: "900" }}>{ativas.length}</Text>
                  <Text style={{ color: "#C0D0E8", fontSize: 13 }}>{ativas.length === 1 ? "reserva ativa" : "reservas ativas"}</Text>
                </View>
              </View>
              <Text style={{ fontSize: 19, fontWeight: "800", color: "#15233B", marginBottom: 12 }}>Reservas ativas</Text>
              {ativas.length ? ativas.map(cartaoReserva) : (
                <View style={{ borderRadius: 18, backgroundColor: "#FFFFFF", padding: 22, marginBottom: 24, alignItems: "center", gap: 8 }}>
                  <Ionicons name="car-outline" size={28} color="#2563EB" />
                  <Text style={{ color: "#15233B", fontSize: 15, fontWeight: "800" }}>Nenhuma reserva ativa</Text>
                  <Text style={{ color: "#64748B", fontSize: 12, textAlign: "center" }}>Encontre um shopping para garantir uma vaga.</Text>
                  <Pressable onPress={() => router.push("/explorar")} accessibilityRole="button" style={{ backgroundColor: "#2563EB", borderRadius: 12, paddingHorizontal: 18, paddingVertical: 11, marginTop: 5 }}>
                    <Text style={{ color: "#FFFFFF", fontWeight: "800" }}>Explorar vagas</Text>
                  </Pressable>
                </View>
              )}
              {historico.length > 0 ? (
                <View style={{ marginTop: ativas.length ? 16 : 0 }}>
                  <Text style={{ fontSize: 19, fontWeight: "800", color: "#15233B", marginBottom: 12 }}>Histórico</Text>
                  {historico.map(cartaoReserva)}
                </View>
              ) : null}
            </>
          )}
        </ScrollView>
        <MobileBottomNav active="reservas" />
      </View>
    );
  }

  return (
    <View className={pagina} style={Platform.OS === "web" ? undefined : { backgroundColor: "#F3F7FD" }}>
      {Platform.OS === "web" ? (
        <Header rotaAtual="/" />
      ) : (
        <MobileScreenHeader title="Reservas" subtitle="Gerencie as vagas que você garantiu" />
      )}
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 48 }}>
        <View className="mx-auto w-full max-w-3xl">
          <Text className="text-2xl font-extrabold text-slate-900 3xl:text-3xl">
            Minhas reservas
          </Text>
          <Text className={textoApoio}>
            Acompanhe e gerencie as vagas que você garantiu.
          </Text>

          {/* Regra do pico-fim: o resumo positivo aparece logo ao entrar. */}
          {isAuthenticated && !loading && !erro && reservas.length > 0 ? (
            <Card className="sp-alerta mt-5 flex-row items-center gap-3 p-4">
              <View className="h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-600">
                <Text className="text-[13px] font-bold text-white">OK</Text>
              </View>
              <View className={minW0Flex1}>
                <Text className={tituloCardShopping}>
                  {reservas.length} {reservas.length === 1 ? "reserva ativa" : "reservas ativas"}
                </Text>
                <Text className={meta}>
                  Suas vagas estão garantidas. Cancele aqui quando não precisar mais.
                </Text>
              </View>
            </Card>
          ) : null}

          <View className="mt-6 gap-3 3xl:gap-6">
            {authLoading || (!isAuthenticated && loading) ? (
              <BlocoCarregando />
            ) : !isAuthenticated ? (
              <BlocoVazio
                nomeIcone="lock-closed-outline"
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
                nomeIcone="car-outline"
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
                    <View className="min-w-0 flex-row flex-wrap items-center gap-4">
                      <View className="h-12 w-12 items-center justify-center rounded-xl bg-blue-600">
                        <Text className="text-[13px] font-extrabold text-white">
                          {codigo.split("-")[1] ?? codigo}
                        </Text>
                      </View>
                      <View className={minW0Flex1}>
                        <View className="min-w-0 flex-row flex-wrap items-center gap-2">
                          <Text className="min-w-0 text-base font-bold text-slate-900">
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
                        <Text className={meta}>
                          {formatarDataHora(r.horario_inicio)} até{" "}
                          {formatarDataHora(r.horario_fim)}
                          {r.observacoes ? ` · ${r.observacoes}` : ""}
                        </Text>
                        <Text style={{ fontSize: 12, color: "#475569", fontWeight: "700", marginTop: 5 }}>
                          {r.veiculo ? `Veículo: ${r.veiculo.placa} · ${r.veiculo.categoria === "moto" ? "Moto" : "Carro"}` : "Veículo não informado (reserva anterior)"}
                        </Text>
                      </View>
                    </View>

                    {/* Apenas reservas ativas podem ser canceladas. Concluída,
                        expirada e cancelada são estados finais no backend. */}
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
      {Platform.OS !== "web" ? <MobileBottomNav active="reservas" /> : null}
    </View>
  );
}
