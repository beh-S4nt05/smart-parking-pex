/**
 * Mapa de vagas — templates "Mapa de Vagas (MOBILE/WEB)" do Figma.
 * - mobile: barra escura com nome do shopping + selo ao vivo; pills de andar;
 *   3 chips de resumo; cartão azul "PRÓXIMA VAGA SUGERIDA"; grade de vagas.
 * - web: conteúdo em 2 colunas com rail lateral (sugestão, resumo do andar,
 *   filtro por tipo).
 * Integração: GET /api/estacionamentos/{id}/vagas (polling), proxima-vaga via
 * motor de atribuição do backend e POST /api/reservas autenticado.
 */
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  Text,
  View,
  useWindowDimensions,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import Header, { BarraEscura } from "../../components/Header";
import VagaMapa from "../../components/VagaMapa";
import { useMapaVagas } from "../../hooks/useMapaVagas";
import { useAgora, desdeAte } from "../../hooks/useAgora";
import { useAuth } from "../../hooks/useAuth";
import { apiErrorMessage, parkingApi } from "../../services/api";
import {
  Botao,
  Card,
  LegendaVagas,
  SeloAoVivo,
  StatTile,
  formatarMoedaBR,
} from "../../components/ui";
import { colors } from "../../theme";
import type {
  Estacionamento,
  ProximaVaga,
  Reserva,
  Vaga,
  VagaTipo,
} from "../../types/api";

const FILTROS_TIPO: { id: VagaTipo | "todos"; label: string }[] = [
  { id: "todos", label: "Todas" },
  { id: "pcd", label: "PCD" },
  { id: "idoso", label: "Idoso" },
  { id: "moto", label: "Moto" },
  { id: "eletrico", label: "Elétrico" },
];

export default function MapaVagas() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { width } = useWindowDimensions();
  const isWeb = width >= 1024;

  const { mapa, setMapa, loading, erro, atualizadoEm, refresh, resumo } =
    useMapaVagas(id, { pollingMs: 20000 });
  const agora = useAgora(5000);
  const { isAuthenticated } = useAuth();

  const [andarSel, setAndarSel] = useState<number | null>(null);
  const [filtroTipo, setFiltroTipo] = useState<VagaTipo | "todos">("todos");
  const [vagaSel, setVagaSel] = useState<Vaga | null>(null);
  const [sugestao, setSugestao] = useState<ProximaVaga | null>(null);
  const [reservando, setReservando] = useState(false);
  const [shopping, setShopping] = useState<Estacionamento | null>(null);
  const [minhasReservas, setMinhasReservas] = useState<Reserva[]>([]);

  // reservas ativas do usuário — dão o botão "Cancelar reserva" no mapa
  useEffect(() => {
    if (!isAuthenticated) {
      setMinhasReservas([]);
      return;
    }
    let alive = true;
    parkingApi
      .minhasReservas()
      .then((r) => alive && setMinhasReservas(r))
      .catch(() => alive && setMinhasReservas([]));
    return () => {
      alive = false;
    };
  }, [isAuthenticated, atualizadoEm]);

  const reservaDestaVaga =
    vagaSel != null
      ? minhasReservas.find(
          (r) => r.status === "confirmada" && r.vaga?.id === vagaSel.id,
        ) ?? null
      : null;

  function pedirCancelamentoReserva(reservaId: string, codigo: string) {
    Alert.alert(
      "Cancelar reserva",
      `A vaga ${codigo} volta a ficar livre no mapa imediatamente.`,
      [
        { text: "Manter", style: "cancel" },
        {
          text: "Cancelar reserva",
          style: "destructive",
          onPress: async () => {
            try {
              await parkingApi.cancelarReserva(reservaId);
              setMinhasReservas((prev) =>
                prev.map((x) =>
                  x.id === reservaId ? { ...x, status: "cancelada" as never } : x,
                ),
              );
              setMapa(
                mapa
                  ? {
                      ...mapa,
                      vagas: mapa.vagas.map((x) =>
                        x.id === vagaSel?.id
                          ? { ...x, status: "livre" as const }
                          : x,
                      ),
                    }
                  : mapa,
              );
              setVagaSel(null);
              refresh();
              Alert.alert("Reserva cancelada", `A vaga ${codigo} foi liberada. ✅`);
            } catch (e) {
              Alert.alert("Não foi possível cancelar", apiErrorMessage(e));
            }
          },
        },
      ],
    );
  }

  const andares = useMemo(() => {
    if (!mapa) return [];
    return [...mapa.andares].sort((a, b) => a.numero_andar - b.numero_andar);
  }, [mapa]);

  useEffect(() => {
    if (andares.length && andarSel == null) setAndarSel(andares[0].numero_andar);
  }, [andares, andarSel]);

  // metadados do shopping (endereço/taxa) para o cabeçalho + resumo
  useEffect(() => {
    if (!id) return;
    let alive = true;
    parkingApi
      .listarEstacionamentos()
      .then((lista) => {
        if (alive) setShopping(lista.find((e) => e.id === id) ?? null);
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [id]);

  const vagasDoAndar = useMemo(() => {
    if (!mapa || andarSel == null) return [];
    const andarId = mapa.andares.find((a) => a.numero_andar === andarSel)?.id;
    return mapa.vagas.filter((v) => v.andar_id === andarId);
  }, [mapa, andarSel]);

  const vagasFiltradas = useMemo(
    () =>
      filtroTipo === "todos"
        ? vagasDoAndar
        : vagasDoAndar.filter((v) => v.tipo === filtroTipo),
    [vagasDoAndar, filtroTipo],
  );

  // motor de atribuição do backend para o andar/tipo exibidos
  useEffect(() => {
    if (!id) return;
    let alive = true;
    parkingApi
      .proximaVaga(id, filtroTipo === "todos" ? undefined : filtroTipo)
      .then((r) => alive && setSugestao(r))
      .catch(() => alive && setSugestao(null));
    return () => {
      alive = false;
    };
  }, [id, filtroTipo, atualizadoEm]);

  const resumoAndar = resumo.porAndar(
    mapa?.andares.find((a) => a.numero_andar === andarSel)?.id,
  );

  function destacarSugestao() {
    const v = sugestao?.vaga;
    if (!v) return;
    if (v.numero_andar != null) setAndarSel(v.numero_andar);
    setVagaSel(v);
    if (!isWeb) {
      // mobile: scroll até a grade (destaque visual já aplicado na célula)
      Alert.alert("Vaga destacada", `${v.codigo} · ${sugestao?.mensagem ?? ""}`);
    }
  }

  async function reservar(v: Vaga) {
    if (!isAuthenticated) {
      Alert.alert("Entre para reservar", "Crie sua conta ou faça login para garantir a vaga.", [
        { text: "Agora não", style: "cancel" },
        { text: "Entrar", onPress: () => router.push("/login") },
      ]);
      return;
    }
    setReservando(true);
    try {
      const ini = new Date(Date.now() + 15 * 60000);
      const fim = new Date(ini.getTime() + 2 * 3600000);
      await parkingApi.criarReserva({
        vaga_id: v.id,
        horario_inicio: ini.toISOString().slice(0, 19),
        horario_fim: fim.toISOString().slice(0, 19),
        observacoes: "Reserva pelo app (2 horas)",
      });
      setMapa(
        mapa
          ? {
              ...mapa,
              vagas: mapa.vagas.map((x) =>
                x.id === v.id ? { ...x, status: "reservada" as const } : x,
              ),
            }
          : mapa,
      );
      setVagaSel(null);
      refresh();
      Alert.alert(
        "Vaga reservada 🎉",
        `${v.codigo} reservada por 2 horas.\nConfira em "Minhas reservas".`,
        isWeb
          ? [
              { text: "Fechar", style: "cancel" },
              {
                text: "Ver reservas",
                onPress: () => router.push("/reservas"),
              },
            ]
          : [{ text: "Ok" }],
      );
    } catch (e) {
      Alert.alert("Não foi possível reservar", apiErrorMessage(e));
    } finally {
      setReservando(false);
    }
  }

  const titulo = mapa?.estacionamento_nome ?? "Mapa de vagas";
  const subtitulo = `${
    shopping ? `${(shopping.endereco ?? "").split(" - ").slice(-1)[0]?.split(",")[0] ?? "Manaus, AM"}` : "Manaus, AM"
  } · atualizado ${desdeAte(atualizadoEm, agora)}`;

  const painelSugerida = (
    <View
      className="rounded-2xl p-5"
      style={{ backgroundColor: colors.primary }}
    >
      <Text className="text-[11px] font-bold uppercase tracking-wider text-blue-200">
        Próxima vaga sugerida
      </Text>
      <Text className="mt-1 text-4xl font-extrabold text-white">
        {sugestao?.vaga?.codigo ?? "—"}
      </Text>
      <Text className="mt-1 text-sm text-blue-100">
        {sugestao?.vaga
          ? `${sugestao.andar_numero}º andar · Vaga ${sugestao.vaga.tipo}`
          : "Sem vagas com esse filtro no momento"}
      </Text>
      {sugestao?.vaga ? (
        <Botao
          label={isWeb ? "Destacar no mapa" : "Ver no mapa"}
          onPress={destacarSugestao}
          className="mt-4 bg-white active:bg-blue-50"
        />
      ) : null}
    </View>
  );

  const gradeVagas = (
    <Card className="p-4 sm:p-6">
      {!isWeb ? (
        <View className="mb-4 flex-row flex-wrap gap-2">
          {andares.map((a) => {
            const ativo = a.numero_andar === andarSel;
            return (
              <Pressable
                key={a.id}
                onPress={() => {
                  setAndarSel(a.numero_andar);
                  setVagaSel(null);
                }}
                className={`rounded-full px-4 py-2 ${
                  ativo ? "bg-blue-600" : "border border-slate-200 bg-white"
                }`}
              >
                <Text
                  className={`text-[13px] font-semibold ${ativo ? "text-white" : "text-slate-600"}`}
                >
                  {a.numero_andar}º andar
                </Text>
              </Pressable>
            );
          })}
        </View>
      ) : (
        <View className="mb-5 flex-row items-center justify-between">
          <View className="flex-row gap-2">
            {andares.map((a) => {
              const ativo = a.numero_andar === andarSel;
              return (
                <Pressable
                  key={a.id}
                  onPress={() => {
                    setAndarSel(a.numero_andar);
                    setVagaSel(null);
                  }}
                  className={`rounded-full px-4 py-2 ${
                    ativo ? "bg-blue-600" : "border border-slate-200 bg-white"
                  }`}
                >
                  <Text
                    className={`text-[13px] font-semibold ${ativo ? "text-white" : "text-slate-600"}`}
                  >
                    {a.numero_andar}º andar
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </View>
      )}

      {filtroTipo !== "todos" && !isWeb ? (
        <View className="mb-4 flex-row flex-wrap gap-2">
          {FILTROS_TIPO.map((f) => (
            <FiltroPill
              key={f.id}
              item={f}
              ativo={filtroTipo === f.id}
              onPress={() => setFiltroTipo(f.id)}
            />
          ))}
        </View>
      ) : null}

      {vagasFiltradas.length === 0 && !loading ? (
        <View className="items-center py-12">
          <Text className="text-base font-semibold text-slate-500">
            Nenhuma vaga exibida — troque o filtro ou o andar.
          </Text>
        </View>
      ) : (
        <VagaMapa
          vagas={vagasFiltradas}
          destaqueId={vagaSel?.id}
          onPressVaga={(v) => setVagaSel((p) => (p?.id === v.id ? null : v))}
        />
      )}

      <View className="mt-5">
        <LegendaVagas />
      </View>

      {/* seleção no mobile → barra de ação */}
      {vagaSel && !isWeb ? (
        <View className="mt-4 rounded-2xl border border-blue-200 bg-blue-50 p-4">
          <Text className="text-[13px] font-semibold text-slate-700">
            Vaga {vagaSel.codigo} ·{" "}
            {vagaSel.status === "livre" ? "disponível" : vagaSel.status}
          </Text>
          {vagaSel.status === "livre" ? (
            <Botao
              label={`Reservar por 2h${shopping?.taxa_hora ? ` · ${formatarMoedaBR(shopping.taxa_hora * 2)}` : ""}`}
              onPress={() => reservar(vagaSel)}
              loading={reservando}
              className="mt-3 w-full"
            />
          ) : reservaDestaVaga ? (
            <Botao
              label="Cancelar minha reserva"
              variant="contorno"
              className="mt-3 w-full border-red-300"
              onPress={() => pedirCancelamentoReserva(reservaDestaVaga.id, vagaSel.codigo)}
            />
          ) : (
            <Text className="mt-1 text-xs text-slate-500">
              Vaga indisponível para reserva neste momento.
            </Text>
          )}
        </View>
      ) : null}
    </Card>
  );

  const conteudo = (
    <View className="gap-5">
      {!isWeb ? (
        <View className="flex-row gap-2.5">
          <View className="flex-1">
            <StatTile rotulo="Livres" valor={String(resumoAndar.livres)} tone="verde" />
          </View>
          <View className="flex-1">
            <StatTile
              rotulo="Ocupadas"
              valor={String(resumoAndar.ocupadas)}
              tone="vermelho"
            />
          </View>
          <View className="flex-1">
            <StatTile
              rotulo="Reservadas"
              valor={String(resumoAndar.reservadas)}
              tone="ambar"
            />
          </View>
        </View>
      ) : null}

      {isWeb ? (
        <View className="flex-row items-start gap-5">
          <View style={{ flex: 2.4 }}>{gradeVagas}</View>
          <View className="flex-1 gap-5" style={{ minWidth: 280 }}>
            {painelSugerida}
            <Card className="p-5">
              <Text className="text-base font-bold text-slate-900">
                {andarSel}º andar — resumo
              </Text>
              <View className="mt-3 gap-2.5">
                <LinhaResumo cor="#10B981" rotulo="Livres" valor={resumoAndar.livres} />
                <LinhaResumo cor="#EF4444" rotulo="Ocupadas" valor={resumoAndar.ocupadas} />
                <LinhaResumo cor="#F59E0B" rotulo="Reservadas" valor={resumoAndar.reservadas} />
              </View>
            </Card>
            <Card className="p-5">
              <Text className="text-base font-bold text-slate-900">
                Filtrar por tipo
              </Text>
              <View className="mt-3 flex-row flex-wrap gap-2">
                {FILTROS_TIPO.map((f) => (
                  <FiltroPill
                    key={f.id}
                    item={f}
                    ativo={filtroTipo === f.id}
                    onPress={() => setFiltroTipo(f.id)}
                  />
                ))}
              </View>
            </Card>
            {vagaSel ? (
              <Card className="border-blue-200 bg-blue-50 p-5">
                <Text className="text-base font-bold text-slate-900">
                  Vaga {vagaSel.codigo} · {vagaSel.status}
                </Text>
                <Text className="mt-1 text-[13px] text-slate-600">
                  {shopping?.taxa_hora
                    ? `Estadia estimada de 2h: ${formatarMoedaBR(shopping.taxa_hora * 2)}`
                    : "Reserve pelo app e pague na saída."}
                </Text>
                {vagaSel.status === "livre" ? (
                  <Botao
                    label="Reservar por 2h"
                    onPress={() => reservar(vagaSel)}
                    loading={reservando}
                    className="mt-3 w-full"
                  />
                ) : reservaDestaVaga ? (
                  <Botao
                    label="Cancelar minha reserva"
                    variant="contorno"
                    className="mt-3 w-full border-red-300"
                    onPress={() =>
                      pedirCancelamentoReserva(reservaDestaVaga.id, vagaSel.codigo)
                    }
                  />
                ) : null}
              </Card>
            ) : null}
          </View>
        </View>
      ) : (
        <>
          {painelSugerida}
          {gradeVagas}
        </>
      )}
    </View>
  );

  // -------- shell mobile (barra escura) --------
  if (!isWeb) {
    return (
      <View className="flex-1 bg-slate-50">
        <BarraEscura
          titulo={titulo}
          subtitulo={subtitulo}
          aoVivo
          voltar={
            <Pressable
              onPress={() => router.back()}
              accessibilityRole="button"
              className="h-9 w-9 items-center justify-center rounded-full bg-white"
            >
              <Text className="text-base font-bold text-slate-900">←</Text>
            </Pressable>
          }
        />
        <ScrollView
          contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
          refreshControl={
            <RefreshControl refreshing={false} onRefresh={refresh} tintColor="#2563EB" />
          }
        >
          {erro ? (
            <View className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
              <Text className="text-[13px] font-medium text-amber-700">⚠️ {erro}</Text>
            </View>
          ) : null}
          {loading && !mapa ? (
            <View className="items-center py-20">
              <ActivityIndicator size="large" color={colors.primary} />
            </View>
          ) : (
            conteudo
          )}
        </ScrollView>
      </View>
    );
  }

  // -------- shell web (header público + título) --------
  return (
    <View className="flex-1 bg-slate-50">
      <Header rotaAtual="/" />
      <ScrollView
        contentContainerStyle={{ padding: 28, paddingBottom: 48 }}
        refreshControl={
          <RefreshControl refreshing={false} onRefresh={refresh} tintColor="#2563EB" />
        }
      >
        <View className="mx-auto w-full max-w-7xl">
          <View className="mb-6 flex-row flex-wrap items-end justify-between">
            <View>
              <Text className="text-3xl font-extrabold text-slate-900">{titulo}</Text>
              <Text className="mt-1 text-sm text-slate-500">{subtitulo}</Text>
            </View>
            <SeloAoVivo />
          </View>
          {erro ? (
            <View className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
              <Text className="text-[13px] font-medium text-amber-700">⚠️ {erro}</Text>
            </View>
          ) : null}
          {loading && !mapa ? (
            <View className="items-center py-24">
              <ActivityIndicator size="large" color={colors.primary} />
            </View>
          ) : (
            conteudo
          )}
        </View>
      </ScrollView>
    </View>
  );
}

function FiltroPill({
  item,
  ativo,
  onPress,
}: {
  item: { id: string; label: string };
  ativo: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      className={`rounded-full border px-3.5 py-1.5 ${
        ativo ? "border-blue-600 bg-blue-50" : "border-slate-200 bg-white"
      }`}
    >
      <Text
        className={`text-[12px] font-semibold ${
          ativo ? "text-blue-700" : "text-slate-500"
        }`}
      >
        {item.label}
      </Text>
    </Pressable>
  );
}

function LinhaResumo({
  cor,
  rotulo,
  valor,
}: {
  cor: string;
  rotulo: string;
  valor: number;
}) {
  return (
    <View className="flex-row items-center justify-between">
      <View className="flex-row items-center gap-2">
        <View className="h-2 w-2 rounded-full" style={{ backgroundColor: cor }} />
        <Text className="text-sm text-slate-600">{rotulo}</Text>
      </View>
      <Text className="text-sm font-extrabold text-slate-900">{valor}</Text>
    </View>
  );
}
