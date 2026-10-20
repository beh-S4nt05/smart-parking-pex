/**
 * Simulador de Sensores (rota aberta via QR) — funciona no celular (câmera →
 * /simulador?sessao=…) e no computador (botão "Abrir simulador" gera a mesma
 * URL). Acesso: SOMENTE o administrador global — a sessão do QR e as rotas de
 * operação exigem JWT de admin, nos dois ambientes.
 *
 * Modos:
 * - "Alternar": um toque inverte o status da vaga (livre↔ocupada) na hora;
 * - "Selecionar": toque marca/desmarca e a barra inferior aplica em lote
 *   (PATCH /api/vagas/lote/status com origem "simulador").
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  Text,
  View,
  useWindowDimensions,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useAuth } from "../hooks/useAuth";
import { useMapaVagas } from "../hooks/useMapaVagas";
import { useAgora, desdeAte } from "../hooks/useAgora";
import { apiErrorMessage, parkingApi } from "../services/api";
import VagaMapa from "../components/VagaMapa";
import { Chip, Logo } from "../components/ui";
import type { SimSession } from "../types/api";

export default function Simulador() {
  const params = useLocalSearchParams<{
    sessao?: string;
    s?: string;
    e?: string;
    a?: string;
  }>();
  const router = useRouter();
  const { isAdmin, isAuthenticated, loading: authLoading } = useAuth();

  const [validando, setValidando] = useState(true);
  const [sessaoOk, setSessaoOk] = useState(false);
  const [motivo, setMotivo] = useState<string | null>(null);
  const [info, setInfo] = useState<SimSession | null>(null);

  const token = params.sessao ?? params.s ?? null;
  const estId = info?.estacionamento_id ?? params.e ?? null;
  const andarNum =
    info?.andar_numero ?? (params.a != null ? Number(params.a) : null);

  // 1) valida o token do QR (rota pública do backend)
  useEffect(() => {
    let alive = true;
    if (!token) {
      setValidando(false);
      setMotivo("Link sem código de sessão.");
      return;
    }
    parkingApi
      .validarSessaoSimulador(token)
      .then((s) => {
        if (!alive) return;
        setInfo(s);
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

  // 2) sessão validada exige login como ADMIN GLOBAL (web e mobile)
  useEffect(() => {
    if (!validando && sessaoOk && !authLoading && !isAdmin) {
      if (!isAuthenticated) {
        router.replace(
          `/login?next=${encodeURIComponent(`/simulador?sessao=${token}`)}` as never,
        );
      }
    }
  }, [validando, sessaoOk, authLoading, isAdmin, isAuthenticated, router, token]);

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
        </View>
      </View>
    );
  }

  if (!isAdmin) {
    return (
      <View className="flex-1 items-center justify-center bg-slate-50 px-8">
        <View className="w-full max-w-sm items-center rounded-2xl border border-slate-200 bg-white p-8">
          <Text className="text-4xl">🔒</Text>
          <Text className="mt-3 text-lg font-extrabold text-slate-900">
            Acesso restrito
          </Text>
          <Text className="mt-1 text-center text-sm text-slate-500">
            O simulador de sensores é exclusivo do administrador global.{" "}
            {isAuthenticated
              ? "Sua conta não tem esse nível de acesso."
              : "Entre com a conta de administrador."}
          </Text>
          <Pressable
            onPress={() =>
              router.replace(isAuthenticated ? "/dashboard" : "/login")
            }
            className="mt-6 w-full items-center rounded-xl bg-blue-600 px-4 py-3 active:bg-blue-700"
          >
            <Text className="text-sm font-bold text-white">
              {isAuthenticated ? "Voltar ao painel" : "Entrar como administrador"}
            </Text>
          </Pressable>
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
  const { width } = useWindowDimensions();
  const isWeb = width >= 1024;
  const { mapa, setMapa, loading, erro, atualizadoEm, refresh } = useMapaVagas(
    estId ?? undefined,
    { pollingMs: 8000 },
  );
  const agora = useAgora(5000);

  const [modo, setModo] = useState<"alternar" | "selecionar">("alternar");
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [enviando, setEnviando] = useState(false);

  const andares = useMemo(
    () =>
      mapa
        ? [...mapa.andares].sort((a, b) => a.numero_andar - b.numero_andar)
        : [],
    [mapa],
  );
  const [andar, setAndar] = useState<number | null>(andarNum);
  useEffect(() => {
    if (
      andares.length &&
      (andar == null || !andares.some((a) => a.numero_andar === andar))
    ) {
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
      setEnviando(true);
      try {
        const res = await parkingApi.atualizarStatusLote(
          alvos,
          destino,
          "simulador",
        );
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
            `${res.atualizadas} vagas atualizadas; ${res.nao_encontradas.length} ignoradas.`,
          );
        }
      } catch (e) {
        Alert.alert("Erro no lote", apiErrorMessage(e));
      } finally {
        setEnviando(false);
      }
    },
    [setMapa, refresh],
  );

  function tocarVaga(id: string, status: string) {
    if (status === "manutencao" || status === "inativa") {
      Alert.alert(
        "Vaga em manutenção",
        "Essa vaga não pode ser operada pelo simulador.",
      );
      return;
    }
    if (modo === "alternar") {
      void aplicarLote([id], status === "livre" ? "ocupada" : "livre");
    } else {
      setSel((p) => {
        const n = new Set(p);
        n.has(id) ? n.delete(id) : n.add(id);
        return n;
      });
    }
  }

  function acaoRapida(tipo: "fechar" | "abrir" | "sortear") {
    if (tipo === "fechar") {
      void aplicarLote(
        vagas.filter((v) => v.status === "livre").slice(0, 12).map((v) => v.id),
        "ocupada",
      );
    } else if (tipo === "abrir") {
      void aplicarLote(
        vagas
          .filter((v) => v.status === "ocupada" || v.status === "reservada")
          .map((v) => v.id),
        "livre",
      );
    } else {
      const virarOcupada = vagas
        .filter((v) => v.status === "livre")
        .slice(0, 6)
        .map((v) => v.id);
      const virarLivre = vagas
        .filter((v) => v.status === "ocupada" || v.status === "reservada")
        .slice(0, 6)
        .map((v) => v.id);
      void aplicarLote(virarOcupada, "ocupada").then(() =>
        aplicarLote(virarLivre, "livre"),
      );
    }
  }

  const conteudo = (
    <View className="gap-3">
      {erro ? (
        <View className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2">
          <Text className="text-xs text-amber-700">⚠️ {erro}</Text>
        </View>
      ) : null}

      {andares.length > 1 ? (
        <View className="flex-row flex-wrap gap-2">
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
                  {a.numero_andar}º andar
                </Text>
              </Pressable>
            );
          })}
        </View>
      ) : null}

      {/* resumo + modos + ações rápidas */}
      <View className="flex-row flex-wrap items-center gap-2">
        <View className="flex-row gap-2">
          {[
            { rot: "Livres", v: contagem.livre ?? 0, cor: "text-emerald-600" },
            {
              rot: "Ocupadas",
              v: (contagem.ocupada ?? 0) + (contagem.reservada ?? 0),
              cor: "text-red-500",
            },
            { rot: "Sel.", v: sel.size, cor: "text-blue-600" },
          ].map((s) => (
            <View
              key={s.rot}
              className="min-w-[86px] flex-1 items-center rounded-xl border border-slate-200 bg-white py-2"
            >
              <Text className={`text-lg font-extrabold ${s.cor}`}>{s.v}</Text>
              <Text className="text-[11px] font-medium text-slate-500">{s.rot}</Text>
            </View>
          ))}
        </View>
        <View className="ml-auto flex-row gap-2">
          {(["alternar", "selecionar"] as const).map((m) => (
            <Pressable
              key={m}
              onPress={() => {
                setModo(m);
                if (m === "alternar") setSel(new Set());
              }}
              className={`rounded-full px-3.5 py-1.5 ${
                modo === m ? "bg-slate-900" : "border border-slate-300 bg-white"
              }`}
            >
              <Text
                className={`text-xs font-bold capitalize ${
                  modo === m ? "text-white" : "text-slate-600"
                }`}
              >
                {m === "alternar" ? "👆 Alternar" : "☑ Selecionar"}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>

      <View className="flex-row flex-wrap gap-2">
        <BotaoLote label="Fechar andar" onPress={() => acaoRapida("fechar")} />
        <BotaoLote label="Abrir andar" onPress={() => acaoRapida("abrir")} />
        <BotaoLote label="Sortear 12" onPress={() => acaoRapida("sortear")} />
      </View>

      <View className="rounded-2xl border border-slate-200 bg-white p-4">
        {loading && !mapa ? (
          <View className="items-center py-16">
            <ActivityIndicator size="large" color="#2563EB" />
          </View>
        ) : (
          <VagaMapa
            vagas={vagas}
            selecionadas={modo === "selecionar" ? sel : undefined}
            onPressVaga={(v) => tocarVaga(v.id, v.status)}
            rotuloInferior="status"
          />
        )}
        <Text className="mt-3 text-center text-[11px] text-slate-400">
          {modo === "alternar"
            ? "Toque na vaga para inverter o status (o painel reflete em segundos)."
            : "Toque para marcar as vagas e aplique em lote na barra abaixo."}
        </Text>
      </View>
    </View>
  );

  return (
    <View className="flex-1 bg-slate-50">
      {/* cabeçalho escuro do simulador (idêntico no web e no mobile) */}
      <View className="bg-slate-950 px-4 pb-5 pt-4">
        <View className="mx-auto flex w-full max-w-5xl flex-row items-center justify-between">
          <View className="flex-row items-center gap-2">
            <Logo size={26} tone="white" />
            <Text className="text-[15px] font-extrabold text-white">
              Simulador de Sensores
            </Text>
            <Chip label="ADMIN" tone="neutro" />
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
        <Text className="mx-auto mt-2 max-w-5xl text-xs text-slate-400">
          {mapa?.estacionamento_nome ?? "…"}
          {andar != null ? ` · ${andar}º andar` : ""} · sessão via QR ·{" "}
          {user?.nome ?? "admin"} · atualizado {desdeAte(atualizadoEm, agora)}
          {isWeb ? " · (funciona igual no celular)" : ""}
        </Text>
      </View>

      <ScrollView contentContainerStyle={{ padding: 14, paddingBottom: 96 }}>
        <View className="mx-auto w-full max-w-5xl">{conteudo}</View>
      </ScrollView>

      {/* barra de lote (modo selecionar) */}
      {sel.size > 0 ? (
        <View className="border-t border-slate-200 bg-white px-4 py-3">
          <View className="mx-auto flex w-full max-w-5xl flex-row items-center gap-2">
            <Text className="flex-1 text-sm font-bold text-slate-800">
              {sel.size} selecionada{sel.size > 1 ? "s" : ""}
            </Text>
            {enviando ? (
              <ActivityIndicator color="#2563EB" />
            ) : (
              <>
                <BotaoLote
                  label="Ocupar"
                  cor="bg-red-500"
                  onPress={() => aplicarLote([...sel], "ocupada")}
                />
                <BotaoLote
                  label="Liberar"
                  cor="bg-emerald-500"
                  onPress={() => aplicarLote([...sel], "livre")}
                />
              </>
            )}
            <Pressable onPress={() => setSel(new Set())} hitSlop={8}>
              <Text className="text-sm font-bold text-slate-400">✕</Text>
            </Pressable>
          </View>
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
      <Text className={`text-[13px] font-bold ${cor ? "text-white" : "text-slate-700"}`}>
        {label}
      </Text>
    </Pressable>
  );
}
