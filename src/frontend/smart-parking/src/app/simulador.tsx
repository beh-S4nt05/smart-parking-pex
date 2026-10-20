/**
 * Simulador de Sensores (rota aberta via QR) — mobile-first, como o fluxo
 * "Admin - Simulador (QR) · MOBILE" do Figma.
 * A URL do QR chega como /simulador?s={token}&e={est}&a={andar}: validamos o
 * token em /auth/simulador/validar (rota pública), e o restante do fluxo usa
 * os endpoints autenticados (o admin precisa estar logado no app — mesma
 * sessão web/mobile). Toque na vaga = inverte o status (origem 'app').
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useAuth } from "../hooks/useAuth";
import { useMapaVagas } from "../hooks/useMapaVagas";
import { apiErrorMessage, parkingApi } from "../services/api";
import { Chip, Logo } from "../components/ui";
import { useAgora, desdeAte } from "../hooks/useAgora";
import type { Vaga } from "../types/api";

export default function Simulador() {
  const params = useLocalSearchParams<{ s?: string; e?: string; a?: string }>();
  const router = useRouter();
  const { isAuthenticated, canAccessPanel, loading: authLoading } = useAuth();

  const [validando, setValidando] = useState(true);
  const [sessaoOk, setSessaoOk] = useState(false);
  const [motivo, setMotivo] = useState<string | null>(null);

  const token = params.s ?? null;
  const estId = params.e ?? null;
  const andarNum = params.a ? Number(params.a) : null;

  // 1) valida o token do QR (rota pública)
  useEffect(() => {
    let alive = true;
    if (!token) {
      setValidando(false);
      setMotivo("Link sem código de sessão.");
      return;
    }
    parkingApi
      .validarSessaoSimulador(token)
      .then(() => {
        if (!alive) return;
        setSessaoOk(true);
      })
      .catch((e: { response?: { status?: number } }) => {
        if (!alive) return;
        const st = e?.response?.status;
        setMotivo(
          st === 410 || st === 404
            ? "Este QR expirou ou foi revogado. Gere um novo no painel do administrador."
            : "API do simulador indisponível.",
        );
      })
      .finally(() => alive && setValidando(false));
    return () => {
      alive = false;
    };
  }, [token]);

  // 2) sessão validada exige identidade com acesso a escrita
  useEffect(() => {
    if (!validando && sessaoOk && !authLoading && !canAccessPanel) {
      router.replace(`/login?next=${encodeURIComponent(`/simulador?s=${token}`)}` as never);
    }
  }, [validando, sessaoOk, authLoading, canAccessPanel, router, token]);

  if (authLoading || validando) {
    return (
      <View className="flex-1 items-center justify-center gap-3 bg-slate-950">
        <Logo size={44} tone="white" />
        <ActivityIndicator color="#60A5FA" />
        <Text className="text-sm text-slate-400">Validando QR…</Text>
      </View>
    );
  }

  if (!sessaoOk) {
    return (
      <View className="flex-1 items-center justify-center bg-slate-50 px-8">
        <View className="w-full max-w-sm items-center rounded-2xl border border-slate-200 bg-white p-8">
          <Text className="text-4xl">🚫</Text>
          <Text className="mt-3 text-lg font-extrabold text-slate-900">
            QR inválido
          </Text>
          <Text className="mt-1 text-center text-sm text-slate-500">
            {motivo ?? "Gere um novo QR no painel do administrador."}
          </Text>
          <Pressable
            onPress={() => router.replace("/")}
            className="mt-6 w-full items-center rounded-xl bg-blue-600 px-4 py-3 active:bg-blue-700"
          >
            <Text className="text-sm font-bold text-white">Voltar ao início</Text>
          </Pressable>
          {isAuthenticated ? (
            <Pressable
              onPress={() => router.replace("/dashboard")}
              className="mt-2 w-full items-center rounded-xl border border-slate-200 bg-white px-4 py-3 active:bg-slate-50"
            >
              <Text className="text-sm font-bold text-slate-700">Ir para o painel</Text>
            </Pressable>
          ) : null}
        </View>
      </View>
    );
  }

  return <SimuladorInterno token={token!} estId={estId} andarNum={andarNum} />;
}

// ------------------------------------------------------------------ interno
function SimuladorInterno({
  token,
  estId,
  andarNum,
}: {
  token: string;
  estId: string | null;
  andarNum: number | null;
}) {
  const { user } = useAuth();
  const { mapa, setMapa, loading, erro, atualizadoEm, refresh } = useMapaVagas(
    estId ?? undefined,
    { pollingMs: 8000 },
  );
  const agora = useAgora(5000);

  const [sel, setSel] = useState<Set<string>>(new Set());

  const andares = useMemo(
    () => (mapa ? [...mapa.andares].sort((a, b) => a.numero_andar - b.numero_andar) : []),
    [mapa],
  );
  const [andar, setAndar] = useState<number | null>(andarNum);
  useEffect(() => {
    if (andares.length && (andar == null || !andares.some((a) => a.numero_andar === andar))) {
      setAndar(andares[0].numero_andar);
    }
  }, [andares, andar]);

  const vagas = useMemo(() => {
    if (!mapa || andar == null) return [];
    const andarId = mapa.andares.find((a) => a.numero_andar === andar)?.id;
    return mapa.vagas.filter((v) => v.andar_id === andarId);
  }, [mapa, andar]);

  const contagem = useMemo(() => {
    const c: Record<string, number> = {
      livre: 0,
      ocupada: 0,
      reservada: 0,
      manutencao: 0,
    };
    vagas.forEach((v) => (c[v.status] = (c[v.status] ?? 0) + 1));
    return c;
  }, [vagas]);

  const aplicarLote = useCallback(
    async (alvos: string[], destino: "livre" | "ocupada") => {
      if (!alvos.length) return;
      try {
        const res = await parkingApi.atualizarStatusLote(alvos, destino, "simulador");
        setMapa(
          (m) =>
            m && {
              ...m,
              vagas: m.vagas.map((v) =>
                alvos.includes(v.id) ? { ...v, status: destino } : v,
              ),
            },
        );
        setSel(new Set());
        refresh();
        if (res.nao_encontradas.length > 0) {
          Alert.alert(
            "Atualização parcial",
            `${res.atualizadas} vagas atualizadas; ${res.nao_encontradas} ignoradas (andares diferentes no mesmo lote são aceitos pelo backend).`,
          );
        }
      } catch (e) {
        Alert.alert("Erro no lote", apiErrorMessage(e));
      }
    },
    [setMapa, refresh],
  );

  function alternarVaga(v: Vaga) {
    if (v.status === "livre") void aplicarLote([v.id], "ocupada");
    else if (v.status === "ocupada" || v.status === "reservada")
      void aplicarLote([v.id], "livre");
    else
      Alert.alert("Vaga em manutenção", `${v.codigo} não pode ser operada pelo simulador.`);
  }

  function selecionarLote(tipo: "livres" | "ocupadas" | "alternar") {
    if (tipo === "livres") {
      void aplicarLote(vagas.filter((v) => v.status === "livre").slice(0, 12).map((v) => v.id), "ocupada");
    } else if (tipo === "ocupadas") {
      void aplicarLote(vagas.filter((v) => v.status === "ocupada" || v.status === "reservada").map((v) => v.id), "livre");
    } else {
      const livres = vagas.filter((v) => v.status === "livre").slice(0, 6).map((v) => v.id);
      const ocupadasIds = vagas
        .filter((v) => v.status === "ocupada" || v.status === "reservada")
        .slice(0, 6)
        .map((v) => v.id);
      void aplicarLote(livres, "ocupada");
      void aplicarLote(ocupadasIds, "livre");
    }
  }

  return (
    <View className="flex-1 bg-slate-50">
      {/* barra escura do simulador */}
      <View className="bg-slate-950 px-4 pb-5 pt-4">
        <View className="flex-row items-center justify-between">
          <View className="flex-row items-center gap-2">
            <Logo size={26} tone="white" />
            <Text className="text-[15px] font-extrabold text-white">
              Simulador de Sensores
            </Text>
          </View>
          <View className="flex-row items-center gap-2">
            <Chip label={`QR ${token.slice(0, 6)}…`} tone="neutro" />
            <View className="flex-row items-center gap-1.5 rounded-full bg-emerald-500/15 px-2.5 py-1">
              <View className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              <Text className="text-[10px] font-bold uppercase text-emerald-300">
                ao vivo
              </Text>
            </View>
          </View>
        </View>
        <Text className="mt-2 text-xs text-slate-400">
          {mapa?.estacionamento_nome ?? "…"} · {user?.nome ?? "admin"} · atualizado{" "}
          {desdeAte(atualizadoEm, agora)}
        </Text>
      </View>

      <ScrollView contentContainerStyle={{ padding: 14, paddingBottom: 44 }}>
        {erro ? (
          <View className="mb-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2">
            <Text className="text-xs text-amber-700">⚠️ {erro}</Text>
          </View>
        ) : null}

        {andares.length > 1 ? (
          <View className="mb-3 flex-row flex-wrap gap-2">
            {andares.map((a) => {
              const ativo = a.numero_andar === andar;
              return (
                <Pressable
                  key={a.id}
                  onPress={() => {
                    setAndar(a.numero_andar);
                    setSel(new Set());
                  }}
                  className={`rounded-full px-4 py-1.5 ${ativo ? "bg-blue-600" : "border border-slate-200 bg-white"}`}
                >
                  <Text
                    className={`text-[13px] font-semibold ${ativo ? "text-white" : "text-slate-600"}`}
                  >
                    {a.numero_andar}º
                  </Text>
                </Pressable>
              );
            })}
          </View>
        ) : null}

        {/* resumo do andar */}
        <View className="mb-3 flex-row gap-2">
          {[
            { rot: "Livres", v: contagem.livre ?? 0, cor: "text-emerald-600" },
            { rot: "Ocupadas", v: (contagem.ocupada ?? 0) + (contagem.reservada ?? 0), cor: "text-red-500" },
            { rot: "Manut.", v: contagem.manutencao ?? 0, cor: "text-slate-500" },
          ].map((s) => (
            <View
              key={s.rot}
              className="flex-1 items-center rounded-xl border border-slate-200 bg-white py-2.5"
            >
              <Text className={`text-xl font-extrabold ${s.cor}`}>{s.v}</Text>
              <Text className="text-[11px] font-medium text-slate-500">{s.rot}</Text>
            </View>
          ))}
        </View>

        {/* ações em lote */}
        <View className="mb-3 flex-row flex-wrap gap-2">
          <BotaoLote label="Fechar andar" onPress={() => selecionarLote("livres")} />
          <BotaoLote label="Abrir andar" onPress={() => selecionarLote("ocupadas")} />
          <BotaoLote label="Alternar 12" onPress={() => selecionarLote("alternar")} />
        </View>

        {loading && !mapa ? (
          <View className="items-center py-16">
            <ActivityIndicator size="large" color="#2563EB" />
          </View>
        ) : (
          <View className="flex-row flex-wrap gap-1.5">
            {vagas.map((v) => {
              const selecionada = sel.has(v.id);
              const fundo =
                v.status === "livre"
                  ? "bg-emerald-500/15 border-emerald-500"
                  : v.status === "ocupada"
                    ? "bg-red-500/15 border-red-400"
                    : v.status === "reservada"
                      ? "bg-amber-400/20 border-amber-400"
                      : "bg-slate-200/60 border-slate-300";
              return (
                <Pressable
                  key={v.id}
                  onPress={() => alternarVaga(v)}
                  onLongPress={() =>
                    setSel((p) => {
                      const n = new Set(p);
                      n.has(v.id) ? n.delete(v.id) : n.add(v.id);
                      return n;
                    })
                  }
                  className={`h-14 flex-1 items-center justify-center rounded-lg border-2 ${fundo} ${
                    selecionada ? "ring-2 ring-blue-600" : ""
                  }`}
                  style={{ minWidth: 60, maxWidth: "23%" }}
                >
                  <Text className="text-[11px] font-bold text-slate-700">{v.codigo}</Text>
                  <Text
                    className={`text-[9px] font-semibold ${
                      v.status === "livre"
                        ? "text-emerald-600"
                        : v.status === "ocupada"
                          ? "text-red-500"
                          : v.status === "reservada"
                            ? "text-amber-600"
                            : "text-slate-400"
                    }`}
                  >
                    {v.status}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        )}
      </ScrollView>

      {/* barra de lote (seleção por long-press) */}
      {sel.size > 0 ? (
        <View className="flex-row items-center gap-2 border-t border-slate-200 bg-white px-4 py-3">
          <Text className="flex-1 text-sm font-bold text-slate-800">
            {sel.size} selecionada{sel.size > 1 ? "s" : ""}
          </Text>
          <BotaoLote label="Ocupar" onPress={() => aplicarLote([...sel], "ocupada")} cor="bg-red-500" />
          <BotaoLote
            label="Liberar"
            onPress={() => aplicarLote([...sel], "livre")}
            cor="bg-emerald-500"
          />
          <Pressable onPress={() => setSel(new Set())} hitSlop={8}>
            <Text className="text-sm font-bold text-slate-400">✕</Text>
          </Pressable>
        </View>
      ) : null}
    </View>
  );
}

function BotaoLote({
  label,
  onPress,
  cor,
}: {
  label: string;
  onPress: () => void;
  cor?: string;
}) {
  return (
    <Pressable
      onPress={onPress}
      className={`rounded-full px-4 py-2 ${cor ?? "border border-slate-300 bg-white"}`}
    >
      <Text
        className={`text-[13px] font-bold ${cor ? "text-white" : "text-slate-700"}`}
      >
        {label}
      </Text>
    </Pressable>
  );
}
