/**
 * Admin — Simulador QR — template "Admin - Simulador (QR)" do Figma.
 * Passo 1: escolher local · Passo 2: escanear com o celular (QR + URL
 * tokenizada revogável) · lateral: "Como funciona" + "Sessões ativas".
 * Backend: /api/admin/simulador/sessoes (criar/listar/revogar).
 */
import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { useRouter } from "expo-router";
import { useAuth } from "../hooks/useAuth";
import { useEstacionamentos } from "../hooks/useEstacionamentos";
import { apiErrorMessage, parkingApi } from "../services/api";
import { Botao, Card, Chip, Logo } from "../components/ui";
import type { SimSession } from "../types/api";

export default function SimuladorQR() {
  const router = useRouter();
  const { loading: authLoading, canAccessPanel, isAuthenticated } = useAuth();
  const { estacionamentos } = useEstacionamentos();

  const [estId, setEstId] = useState<string | null>(null);
  const [andar, setAndar] = useState<number | null>(null);
  const [duracao, setDuracao] = useState(12);
  const [sessao, setSessao] = useState<SimSession | null>(null);
  const [sessoes, setSessoes] = useState<SimSession[]>([]);
  const [gerando, setGerando] = useState(false);
  const [copiando, setCopiando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && (!isAuthenticated || !canAccessPanel)) {
      router.replace("/login");
    }
  }, [authLoading, isAuthenticated, canAccessPanel, router]);

  const est = estacionamentos.find((e) => e.id === estId) ?? null;

  useEffect(() => {
    if (est) {
      const nums = est.andares
        .map((a) => a.numero_andar)
        .sort((a, b) => a - b);
      setAndar((atual) => (atual != null && nums.includes(atual) ? atual : (nums[0] ?? null)));
    }
  }, [est]);

  const listarSessoes = useCallback(async () => {
    try {
      setSessoes(await parkingApi.listarSessoesSimulador());
    } catch {
      /* silencioso: lista é apoio */
    }
  }, []);

  useEffect(() => {
    if (canAccessPanel) listarSessoes();
  }, [canAccessPanel, listarSessoes]);

  async function gerar() {
    if (!estId || andar == null) {
      setErro("Escolha o estacionamento e o andar.");
      return;
    }
    setGerando(true);
    setErro(null);
    try {
      const s = await parkingApi.criarSessaoSimulador(estId, andar, duracao);
      setSessao(s);
      listarSessoes();
    } catch (e) {
      setErro(apiErrorMessage(e, "Não foi possível gerar a sessão."));
    } finally {
      setGerando(false);
    }
  }

  async function copiar() {
    if (!sessao?.url) return;
    const url = sessao.url;
    setCopiando(true);
    try {
      if (Platform.OS === "web") {
        // expo-clipboard não é dependência do projeto → web API direta
        await (globalThis as { navigator?: { clipboard?: { writeText: (t: string) => Promise<void> } } })
          .navigator?.clipboard?.writeText(url);
        Alert.alert("Link copiado!", "Cole no navegador do celular para abrir o simulador.");
      } else {
        Alert.alert("Copie o link", url);
      }
    } catch {
      Alert.alert("Copie o link manualmente", url);
    } finally {
      setCopiando(false);
    }
  }

  async function revogar() {
    if (!sessao) return;
    Alert.alert("Revogar sessão", "O QR deixa de funcionar imediatamente.", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Revogar",
        style: "destructive",
        onPress: async () => {
          try {
            await parkingApi.revogarSessaoSimulador(sessao.token);
            setSessao(null);
            listarSessoes();
          } catch (e) {
            Alert.alert("Erro", apiErrorMessage(e));
          }
        },
      },
    ]);
  }

  if (authLoading) {
    return (
      <View className="flex-1 items-center justify-center bg-slate-50">
        <ActivityIndicator size="large" color="#2563EB" />
      </View>
    );
  }

  return (
    <View className="flex-1 bg-slate-50">
      {/* topo (mobile) / faixa (web) */}
      <View className="flex-row items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
        <View className="flex-row items-center gap-2.5">
          <Pressable
            onPress={() => router.back()}
            accessibilityRole="button"
            className="h-8 w-8 items-center justify-center rounded-full border border-slate-200"
          >
            <Text className="text-base text-slate-600">←</Text>
          </Pressable>
          <Logo size={30} />
          <View>
            <Text className="text-[15px] font-extrabold text-slate-900">
              Simulador de Sensores
            </Text>
            <Text className="text-[11px] text-slate-500">Gerador de QR · Admin</Text>
          </View>
        </View>
        <Chip label="🛠️ ADMIN" tone="azul" />
      </View>

      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 48 }}>
        <View className="mx-auto w-full max-w-6xl flex-row flex-wrap items-start gap-5">
          {/* coluna principal */}
          <View className="min-w-[300px] flex-1 gap-5" style={{ flexBasis: 520 }}>
            <Card className="p-6">
              <Passo numero="1" titulo="Escolha o local" />
              <View className="mt-4 gap-4">
                <CampoRotulo rotulo="Estacionamento">
                  <ScrollView
                    horizontal
                    showsHorizontalScrollIndicator={false}
                    contentContainerStyle={{ gap: 8 }}
                  >
                    {estacionamentos.map((e) => {
                      const ativo = e.id === estId;
                      return (
                        <Pressable
                          key={e.id}
                          onPress={() => setEstId(e.id)}
                          className={`rounded-full border px-4 py-2 ${
                            ativo ? "border-blue-600 bg-blue-50" : "border-slate-200 bg-white"
                          }`}
                        >
                          <Text
                            className={`text-[13px] font-semibold ${
                              ativo ? "text-blue-700" : "text-slate-600"
                            }`}
                          >
                            {e.nome}
                          </Text>
                        </Pressable>
                      );
                    })}
                  </ScrollView>
                </CampoRotulo>

                <CampoRotulo rotulo="Andar">
                  <View className="flex-row gap-2">
                    {(est?.andares ?? [])
                      .slice()
                      .sort((a, b) => a.numero_andar - b.numero_andar)
                      .map((a) => {
                        const ativo = a.numero_andar === andar;
                        return (
                          <Pressable
                            key={a.id}
                            onPress={() => setAndar(a.numero_andar)}
                            className={`rounded-full border px-4 py-2 ${
                              ativo ? "border-blue-600 bg-blue-50" : "border-slate-200 bg-white"
                            }`}
                          >
                            <Text
                              className={`text-[13px] font-semibold ${
                                ativo ? "text-blue-700" : "text-slate-600"
                              }`}
                            >
                              {a.numero_andar}º andar
                            </Text>
                          </Pressable>
                        );
                      })}
                  </View>
                </CampoRotulo>

                <CampoRotulo rotulo="Validade da sessão">
                  <View className="flex-row gap-2">
                    {[1, 4, 8, 12, 24].map((h) => (
                      <Pressable
                        key={h}
                        onPress={() => setDuracao(h)}
                        className={`rounded-full border px-4 py-2 ${
                          duracao === h
                            ? "border-blue-600 bg-blue-50"
                            : "border-slate-200 bg-white"
                        }`}
                      >
                        <Text
                          className={`text-[13px] font-semibold ${
                            duracao === h ? "text-blue-700" : "text-slate-600"
                          }`}
                        >
                          {h}h
                        </Text>
                      </Pressable>
                    ))}
                  </View>
                </CampoRotulo>

                {erro ? (
                  <Text className="text-[13px] font-medium text-red-600">{erro}</Text>
                ) : null}

                <Botao
                  label={gerando ? "Gerando sessão…" : "Gerar QR Code"}
                  onPress={gerar}
                  loading={gerando}
                  className="w-full"
                />
              </View>
            </Card>

            {sessao ? (
              <Card className="p-6">
                <Passo numero="2" titulo="Escaneie com o celular" />
                <View className="mt-5 flex-row flex-wrap items-center gap-5">
                  <View className="items-center rounded-2xl bg-slate-50 p-4">
                    <Image
                      source={{ uri: `data:image/png;base64,${sessao.qr_png_base64}` }}
                      style={{ width: 168, height: 168 }}
                      resizeMode="contain"
                      accessibilityLabel="QR Code da sessão do simulador"
                    />
                  </View>

                  <View className="min-w-[240px] flex-1 gap-3">
                    <View>
                      <Text className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                        URL da sessão
                      </Text>
                      <View className="mt-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
                        <TextInput
                          value={sessao.url}
                          editable={false}
                                                    className="text-xs text-slate-600"
                        />
                      </View>
                    </View>

                    <View className="flex-row gap-2">
                      <Botao
                        label={copiando ? "Copiando…" : "Copiar link"}
                        variant="contorno"
                        onPress={copiar}
                        className="flex-1"
                      />
                      <Botao
                        label="Abrir simulador"
                        variant="primario"
                        onPress={() =>
                          router.push(
                            `/simulador?sessao=${sessao.token}` as never,
                          )
                        }
                        className="flex-1"
                      />
                    </View>
                    <Botao
                      label="Revogar sessão"
                      variant="contorno"
                      className="w-full border-red-300 text-red-600"
                      onPress={revogar}
                    />
                  </View>
                </View>
              </Card>
            ) : (
              <Card className="items-center border-dashed p-8">
                <Text className="text-3xl">📲</Text>
                <Text className="mt-2 text-sm text-slate-500">
                  Gere o QR no passo 1 para liberar o acesso do celular ao mapa
                  de vagas.
                </Text>
              </Card>
            )}
          </View>

          {/* lateral */}
          <View className="min-w-[260px] flex-1 gap-5" style={{ flexBasis: 300 }}>
            <Card className="p-5">
              <Text className="text-base font-bold text-slate-900">Como funciona</Text>
              <View className="mt-3 gap-3">
                {[
                  "O QR aponta para /simulador no app (mesma URL deste ambiente).",
                  "No celular, faça login — a rota exige papel de administrador ou gestor.",
                  "Toque nas vagas (ou use os lotes) para simular sensores.",
                  "As alterações aparecem no painel em tempo real.",
                ].map((t, i) => (
                  <View key={i} className="flex-row gap-3">
                    <View className="h-6 w-6 items-center justify-center rounded-full bg-blue-100">
                      <Text className="text-[11px] font-bold text-blue-700">{i + 1}</Text>
                    </View>
                    <Text className="flex-1 text-[13px] leading-5 text-slate-600">{t}</Text>
                  </View>
                ))}
              </View>
            </Card>

            <Card className="p-5">
              <Text className="text-base font-bold text-slate-900">Sessões ativas</Text>
              {sessoes.length === 0 ? (
                <Text className="mt-2 text-[13px] text-slate-400">
                  Nenhuma sessão pendente.
                </Text>
              ) : (
                <View className="mt-3 gap-2">
                  {sessoes.map((s) => (
                    <View
                      key={s.token}
                      className="flex-row items-center justify-between rounded-xl border border-slate-100 bg-slate-50 px-3 py-2"
                    >
                      <View className="min-w-0 flex-1">
                        <Text className="text-[13px] font-semibold text-slate-700" numberOfLines={1}>
                          {s.estacionamento_nome} · {s.andar_numero}º
                        </Text>
                        <Text className="text-[11px] text-slate-400">
                          expira {new Date(s.expira_em).toLocaleString("pt-BR", {
                            day: "2-digit",
                            month: "2-digit",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </Text>
                      </View>
                      <Pressable
                        onPress={async () => {
                          try {
                            await parkingApi.revogarSessaoSimulador(s.token);
                            if (sessao?.token === s.token) setSessao(null);
                            listarSessoes();
                          } catch (e) {
                            Alert.alert("Erro", apiErrorMessage(e));
                          }
                        }}
                        hitSlop={8}
                      >
                        <Text className="text-xs font-bold text-red-500">✕</Text>
                      </Pressable>
                    </View>
                  ))}
                </View>
              )}
            </Card>
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

function Passo({ numero, titulo }: { numero: string; titulo: string }) {
  return (
    <View className="flex-row items-center gap-2.5">
      <View className="h-7 w-7 items-center justify-center rounded-full bg-blue-600">
        <Text className="text-[13px] font-bold text-white">{numero}</Text>
      </View>
      <Text className="text-lg font-extrabold text-slate-900">{titulo}</Text>
    </View>
  );
}

function CampoRotulo({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <View>
      <Text className="mb-1.5 text-xs font-semibold text-slate-500">{rotulo}</Text>
      {children}
    </View>
  );
}
