/**
 * Painel administrativo — templates "Admin - Dashboard (MOBILE/WEB)" do Figma.
 * Abas: Dashboard, Estacionamentos, Andares e Vagas, Relatórios, Usuários
 * (Simulador QR leva à rota própria). Web = sidebar escura; mobile = toasts.
 * Dados reais: /api/admin/*, /api/relatorios/*, /api/estacionamentos.
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
import { useRouter } from "expo-router";
import AdminShell, { type AbaPainel } from "../components/AdminShell";
import VagaMapa from "../components/VagaMapa";
import { useAuth } from "../hooks/useAuth";
import { useEstacionamentos } from "../hooks/useEstacionamentos";
import { useMapaVagas } from "../hooks/useMapaVagas";
import { apiErrorMessage, parkingApi } from "../services/api";
import {
  BarraOcupacao,
  Botao,
  Card,
  Campo,
  Chip,
  ModalForma,
  StatTile,
  StatusVagaChip,
  formatarMinutos,
  formatarMoedaBR,
} from "../components/ui";
import { ORIGEM_LABEL, ocupacaoColor } from "../theme";
import type {
  DashboardAdmin,
  EventoVaga,
  Estacionamento,
  OcupacaoAndar,
  Usuario,
} from "../types/api";

const ROLE_LABEL: Record<string, string> = {
  admin: "Admin",
  gestor: "Gestor",
  financeiro: "Financeiro",
  usuario: "Motorista",
  publico: "Público",
};

export default function Dashboard() {
  const router = useRouter();
  const { user, loading: authLoading, isAuthenticated, canAccessPanel, isAdmin } =
    useAuth();
  const [aba, setAba] = useState<AbaPainel>("dashboard");
  const [estSel, setEstSel] = useState<string | null>(null); // null = todos (admin)

  const { estacionamentos, loading: estLoading, refresh: recarregarEstacionamentos } =
    useEstacionamentos({ pollingMs: 30000 });

  useEffect(() => {
    if (!authLoading && (!isAuthenticated || !canAccessPanel)) {
      router.replace("/login");
    }
  }, [authLoading, isAuthenticated, canAccessPanel, router]);

  // gestor/financeiro: trava no estacionamento vinculado
  useEffect(() => {
    if (user?.estacionamento_id) setEstSel(user.estacionamento_id);
  }, [user]);

  const bloqueado = authLoading || !isAuthenticated || !canAccessPanel;
  if (bloqueado) {
    return (
      <View className="flex-1 items-center justify-center bg-slate-50">
        <ActivityIndicator size="large" color="#2563EB" />
      </View>
    );
  }

  const seletor = (
    <SeletorEstacionamento
      estacionamentos={estacionamentos}
      valor={estSel}
      onChange={setEstSel}
      travado={!!user?.estacionamento_id}
    />
  );

  return (
    <AdminShell
      aba={aba}
      onAba={setAba}
      titulo={
        aba === "dashboard"
          ? "Dashboard"
          : aba === "estacionamentos"
            ? "Estacionamentos"
            : aba === "andares"
              ? "Andares e Vagas"
              : aba === "relatorios"
                ? "Relatórios"
                : "Usuários"
      }
      subtitulo={
        aba === "dashboard"
          ? "Visão geral em tempo real"
          : aba === "relatorios"
            ? "Fluxo e ocupação por período"
            : undefined
      }
      direita={seletor}
    >
      {aba === "dashboard" && (
        <AbaDashboard estacionamentos={estacionamentos} estSel={estSel} isAdmin={isAdmin} />
      )}
      {aba === "estacionamentos" && (
        <AbaEstacionamentos
          estacionamentos={estacionamentos}
          onAbrir={(id) => router.push(`/shopping/${id}` as never)}
          podeGerenciar={isAdmin}
          onChanged={recarregarEstacionamentos}
        />
      )}
      {aba === "andares" && <AbaAndares estacionamentos={estacionamentos} estSel={estSel} />}
      {aba === "relatorios" && <AbaRelatorios estSel={estSel} />}
      {aba === "usuarios" && (
        <AbaUsuarios isAdmin={isAdmin} estacionamentos={estacionamentos} onChanged={recarregarEstacionamentos} />
      )}
    </AdminShell>
  );
}

// ==================================================== seletor de shopping
function SeletorEstacionamento({
  estacionamentos,
  valor,
  onChange,
  travado,
}: {
  estacionamentos: Estacionamento[];
  valor: string | null;
  onChange: (id: string | null) => void;
  travado: boolean;
}) {
  // sem ScrollView: no web a roda do mouse não rola horizontal e no Android o
  // scroll vertical pai "come" o gesto — wrap resolve nas duas plataformas
  return (
    <View style={{ maxWidth: 560, flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
      {!travado ? (
        <Pressable
          onPress={() => onChange(null)}
          className={`rounded-full border px-4 py-2 ${
            valor === null ? "border-blue-600 bg-blue-600" : "border-slate-200 bg-white"
          }`}
        >
          <Text
            className={`text-[13px] font-semibold ${
              valor === null ? "text-white" : "text-slate-600"
            }`}
          >
            Todos
          </Text>
        </Pressable>
      ) : null}
      {estacionamentos.map((e) => {
        const ativo = e.id === valor;
        return (
          <Pressable
            key={e.id}
            onPress={() => onChange(e.id)}
            className={`rounded-full border px-4 py-2 ${
              ativo ? "border-blue-600 bg-blue-600" : "border-slate-200 bg-white"
            }`}
          >
            <Text
              className={`text-[13px] font-semibold ${ativo ? "text-white" : "text-slate-600"}`}
            >
              {e.nome}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

// ==================================================== aba dashboard
function AbaDashboard({
  estacionamentos,
  estSel,
  isAdmin,
}: {
  estacionamentos: Estacionamento[];
  estSel: string | null;
  isAdmin: boolean;
}) {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const compacto = width < 768;
  const [admin, setAdmin] = useState<DashboardAdmin | null>(null);
  const [gestor, setGestor] = useState<{
    faturamento_hoje: number;
    ticket_medio_hoje: number;
    total_pagamentos_hoje: number;
  } | null>(null);
  const [fluxo, setFluxo] = useState<{
    total_entradas: number;
    total_saidas: number;
    tempo_medio_permanencia_min: number;
    registros: Array<{ entrada_em: string | null; saida_em: string | null }>;
  } | null>(null);
  const [andares, setAndares] = useState<OcupacaoAndar[]>([]);
  const [eventos, setEventos] = useState<EventoVaga[]>([]);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    try {
      if (isAdmin && !estSel) {
        const d = await parkingApi.dashboardAdmin();
        setAdmin(d);
      } else {
        const d = await parkingApi.dashboardGestor().catch(() => null);
        if (d) setGestor(d as never);
      }
      const f = await parkingApi.fluxoHoje(estSel ?? undefined);
      setFluxo(f);
      if (estSel) {
        const [a, ev] = await Promise.all([
          parkingApi.ocupacaoPorAndar(estSel).catch(() => []),
          parkingApi.listarEventos(estSel, 8).catch(() => []),
        ]);
        setAndares(a as OcupacaoAndar[]);
        setEventos(ev as EventoVaga[]);
      } else {
        setAndares([]);
        const ev = await parkingApi.listarEventos(undefined, 8).catch(() => []);
        setEventos(ev as EventoVaga[]);
      }
      setErro(null);
    } catch (e) {
      setErro(apiErrorMessage(e, "Falha ao carregar o painel."));
    }
  }, [estSel, isAdmin]);

  useEffect(() => {
    carregar();
    const t = setInterval(carregar, 25000);
    return () => clearInterval(t);
  }, [carregar]);

  // agregado global quando "Todos"
  const agregados = useMemo(() => {
    if (estSel) {
      const e = estacionamentos.find((x) => x.id === estSel);
      const total = e?.total_vagas ?? 0;
      const livres = e?.vagas_disponiveis_total ?? 0;
      return {
        livres,
        total,
        ocupacao: total ? Math.round(((total - livres) / total) * 100) : 0,
      };
    }
    const total = estacionamentos.reduce((acc, e) => acc + (e.total_vagas || 0), 0);
    const livres = estacionamentos.reduce(
      (acc, e) => acc + (e.vagas_disponiveis_total || 0),
      0,
    );
    return {
      livres,
      total,
      ocupacao: total ? Math.round(((total - livres) / total) * 100) : 0,
    };
  }, [estacionamentos, estSel]);

  const horas = useMemo(() => {
    // buckets 8h..19h de entradas por hora
    const base = Array.from({ length: 12 }, (_, i) => ({ hora: 8 + i, n: 0 }));
    (fluxo?.registros ?? []).forEach((r) => {
      if (!r.entrada_em) return;
      const h = new Date(r.entrada_em).getHours();
      const idx = h - 8;
      if (idx >= 0 && idx < base.length) base[idx].n += 1;
    });
    const max = Math.max(...base.map((b) => b.n), 1);
    const agoraHora = new Date().getHours();
    return { base, max, agoraHora };
  }, [fluxo]);

  return (
    <View className="gap-5">
      {erro ? (
        <View className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <Text className="text-[13px] font-medium text-amber-700">⚠️ {erro}</Text>
        </View>
      ) : null}

      {/* tiles */}
      <View className="flex-row flex-wrap gap-3">
        <View className="min-w-[150px] flex-1">
          <StatTile
            rotulo="Vagas livres"
            valor={String(agregados.livres)}
            tone="verde"
          />
        </View>
        <View className="min-w-[150px] flex-1">
          <StatTile
            rotulo="Taxa de ocupação"
            valor={`${agregados.ocupacao}%`}
            tone="azul"
          />
        </View>
        <View className="min-w-[150px] flex-1">
          <StatTile
            rotulo="Entradas hoje"
            valor={String(fluxo?.total_entradas ?? 0)}
            tone="neutro"
          />
        </View>
        <View className="min-w-[150px] flex-1">
          <StatTile
            rotulo="Permanência média"
            valor={formatarMinutos(fluxo?.tempo_medio_permanencia_min)}
            tone="roxo"
          />
        </View>
      </View>

      {gestor ? (
        <Text className="text-xs text-slate-500">
          Faturamento hoje: {formatarMoedaBR(gestor.faturamento_hoje)} ·{" "}
          {gestor.total_pagamentos_hoje} pagamentos
        </Text>
      ) : null}

      <View className="flex-row flex-wrap gap-5">
        {/* ocupação por andar */}
        <Card className="flex-1 p-5" style={{ minWidth: 300 }}>
          <Text className="mb-4 text-base font-bold text-slate-900">
            Ocupação por andar
          </Text>
          {andares.length === 0 ? (
            <Text className="text-[13px] text-slate-400">
              Selecione um shopping no topo para ver a divisão por andar.
            </Text>
          ) : (
            <View className="gap-3.5">
              {andares.map((a) => (
                <View key={a.andar_id}>
                  <View className="mb-1.5 flex-row items-center justify-between">
                    <Text className="text-sm font-medium text-slate-600">
                      {a.numero_andar}º andar
                    </Text>
                    <Text className="text-sm font-extrabold text-slate-900">
                      {a.percentual}%
                    </Text>
                  </View>
                  <BarraOcupacao percentual={a.percentual} />
                </View>
              ))}
            </View>
          )}
        </Card>

        {/* fluxo por hora (web) / fluxo hoje (mobile) */}
        <Card className="flex-1 p-5" style={{ minWidth: 300 }}>
          <Text className="mb-4 text-base font-bold text-slate-900">
            Fluxo de veículos por hora
          </Text>
          <View className="h-36 flex-row items-end gap-1.5">
            {horas.base.map((b) => {
              const h = Math.max(6, (b.n / horas.max) * 110);
              const ativoHora = b.hora === horas.agoraHora;
              return (
                <View key={b.hora} className="flex-1 items-center gap-1">
                  <View
                    className="w-full rounded-t-md"
                    style={{
                      height: h,
                      backgroundColor: ativoHora ? "#2563EB" : "#DBEAFE",
                    }}
                  />
                  <Text
                    className={`text-[9px] ${ativoHora ? "font-bold text-blue-600" : "text-slate-400"}`}
                  >
                    {b.hora}h
                  </Text>
                </View>
              );
            })}
          </View>
          <View className="mt-4 flex-row gap-3">
            <View className="flex-1 rounded-xl bg-slate-50 p-3">
              <Text className="text-[11px] font-medium text-slate-500">Entradas</Text>
              <Text className="text-xl font-extrabold text-emerald-600">
                {fluxo?.total_entradas ?? 0}
              </Text>
            </View>
            <View className="flex-1 rounded-xl bg-slate-50 p-3">
              <Text className="text-[11px] font-medium text-slate-500">Saídas</Text>
              <Text className="text-xl font-extrabold text-red-500">
                {fluxo?.total_saidas ?? 0}
              </Text>
            </View>
          </View>
        </Card>
      </View>

      {/* últimos eventos */}
      <Card className="p-5">
        <Text className="mb-3 text-base font-bold text-slate-900">
          Últimos eventos de vagas
        </Text>
        {eventos.length === 0 ? (
          <Text className="text-[13px] text-slate-400">
            Nenhum movimento registrado hoje — altere vagas pelo simulador para
            popular o feed.
          </Text>
        ) : (
          <View>
            {!compacto ? (
              <View className="flex-row items-center gap-3 rounded-lg bg-slate-50 px-3 py-2">
                <HeaderCol w={90} t="Vaga" />
                <HeaderCol w={70} t="Andar" />
                <HeaderCol w={110} t="Status" />
                <HeaderCol w={140} t="Origem" />
                <HeaderCol w={0} t="Horário" flex />
              </View>
            ) : null}
            <View className="mt-1">
              {eventos.map((ev, i) => {
                const hora = ev.momento
                  ? new Date(ev.momento).toLocaleTimeString("pt-BR", {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })
                  : "—";
                const zebrado = i % 2 ? "bg-slate-50/60" : "";
                if (compacto) {
                  // mobile: linha em duas alturas, sem larguras fixas
                  return (
                    <View
                      key={ev.id}
                      className={`gap-1 rounded-lg px-3 py-2.5 ${zebrado}`}
                    >
                      <View className="flex-row items-center justify-between">
                        <Text className="text-sm font-bold text-slate-900">
                          {ev.vaga_codigo}
                          {ev.andar_numero != null
                            ? ` · ${ev.andar_numero}º`
                            : ""}
                        </Text>
                        <Text className="text-xs text-slate-400">{hora}</Text>
                      </View>
                      <View className="flex-row items-center gap-2">
                        <StatusVagaChip status={ev.vaga_status} />
                        <Text className="text-xs text-slate-500">
                          {ORIGEM_LABEL[ev.origem] ?? ev.origem}
                        </Text>
                      </View>
                    </View>
                  );
                }
                return (
                  <View
                    key={ev.id}
                    className={`flex-row items-center gap-3 px-3 py-2.5 ${zebrado}`}
                  >
                    <Text className="w-[80px] text-sm font-bold text-slate-900">
                      {ev.vaga_codigo}
                    </Text>
                    <Text className="w-[60px] text-sm text-slate-600">
                      {ev.andar_numero != null ? `${ev.andar_numero}º` : "—"}
                    </Text>
                    <View className="w-[110px]">
                      <StatusVagaChip status={ev.vaga_status} />
                    </View>
                    <Text className="w-[130px] text-sm text-slate-500">
                      {ORIGEM_LABEL[ev.origem] ?? ev.origem}
                    </Text>
                    <Text className="flex-1 text-xs text-slate-400">{hora}</Text>
                  </View>
                );
              })}
            </View>
          </View>
        )}
      </Card>

      {/* atalho para o simulador */}
      <Card className="flex-row flex-wrap items-center justify-between gap-3 border-blue-200 bg-blue-50 p-5">
        <View>
          <Text className="text-base font-bold text-slate-900">
            Simular entrada/saída de veículos
          </Text>
          <Text className="mt-0.5 text-[13px] text-slate-600">
            Gere o QR do simulador e toque nas vagas pelo celular.
          </Text>
        </View>
        <Botao label="Abrir Simulador QR" onPress={() => router.push("/simulador-qr")} />
      </Card>
    </View>
  );
}

function HeaderCol({ t, w, flex }: { t: string; w: number; flex?: boolean }) {
  return (
    <Text
      className="text-[11px] font-bold uppercase tracking-wide text-slate-400"
      style={flex ? { flex: 1 } : { width: w }}
    >
      {t}
    </Text>
  );
}

// ==================================================== aba estacionamentos
function AbaEstacionamentos({
  estacionamentos,
  onAbrir,
  podeGerenciar,
  onChanged,
}: {
  estacionamentos: Estacionamento[];
  onAbrir: (id: string) => void;
  podeGerenciar: boolean;
  onChanged: () => void;
}) {
  type ModalEst =
    | { tipo: "novo" }
    | { tipo: "andar"; est: Estacionamento }
    | { tipo: "vagas"; est: Estacionamento }
    | null;
  const [modal, setModal] = useState<ModalEst>(null);
  const [ocupado, setOcupado] = useState(false);
  const [novo, setNovo] = useState({
    nome: "",
    endereco: "",
    andares: "2",
    vagas: "60",
    abertura: "06:00",
    fechamento: "23:00",
    taxa: "8",
  });
  const [andarF, setAndarF] = useState({ numero: "1", capacidade: "60" });
  const [loteF, setLoteF] = useState({ andarId: "", quantidade: "40", prefixo: "A" });

  const num = (v: string, fb = 0) => {
    const n = Number(v.replace(",", "."));
    return Number.isFinite(n) ? n : fb;
  };

  function erroSalvar(e: unknown) {
    Alert.alert(
      "Não foi possível salvar",
      e instanceof Error ? e.message : apiErrorMessage(e),
    );
  }

  async function salvar() {
    if (!modal) return;
    setOcupado(true);
    try {
      if (modal.tipo === "novo") {
        if (novo.nome.trim().length < 2) throw new Error("Informe o nome do estacionamento");
        await parkingApi.criarEstacionamento({
          nome: novo.nome.trim(),
          endereco: novo.endereco.trim() || undefined,
          total_andares: Math.max(1, Math.round(num(novo.andares, 1))),
          total_vagas: Math.max(0, Math.round(num(novo.vagas, 0))),
          hora_abertura: novo.abertura || "06:00",
          hora_fechamento: novo.fechamento || "23:00",
          taxa_hora: Math.max(0, num(novo.taxa, 0)),
        });
        Alert.alert(
          "Estacionamento criado ✅",
          "Agora adicione os andares e gere as vagas em lote para o mapa funcionar.",
        );
      } else if (modal.tipo === "andar") {
        await parkingApi.criarAndar({
          estacionamento_id: modal.est.id,
          numero_andar: Math.round(num(andarF.numero, 1)),
          capacidade: Math.max(1, Math.round(num(andarF.capacidade, 10))),
        });
        Alert.alert("Andar criado ✅", "Use “Vagas em lote” para popular o mapa dele.");
      } else {
        if (!loteF.andarId) throw new Error("Escolha o andar que vai receber as vagas");
        const criadas = await parkingApi.criarVagasEmLote({
          andar_id: loteF.andarId,
          quantidade: Math.min(500, Math.max(1, Math.round(num(loteF.quantidade, 10)))),
          prefixo_codigo: (loteF.prefixo || "A").toUpperCase().slice(0, 2),
        });
        Alert.alert("Vagas geradas ✅", `${criadas.length} vagas criadas com códigos em sequência.`);
      }
      setModal(null);
      onChanged();
    } catch (e) {
      erroSalvar(e);
    } finally {
      setOcupado(false);
    }
  }

  function excluir(est: Estacionamento) {
    Alert.alert(
      "Excluir estacionamento",
      `Remove ${est.nome} com TODOS os andares, vagas e históricos. Não tem volta.`,
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Excluir definitivamente",
          style: "destructive",
          onPress: async () => {
            try {
              await parkingApi.excluirEstacionamento(est.id);
              Alert.alert("Removido", `${est.nome} saiu da rede credenciada.`);
              onChanged();
            } catch (e) {
              Alert.alert("Erro", apiErrorMessage(e));
            }
          },
        },
      ],
    );
  }

  const andaresDoLote = modal?.tipo === "vagas" ? modal.est.andares : [];

  return (
    <View className="gap-3">
      {podeGerenciar ? (
        <View className="flex-row justify-end">
          <Botao
            label="＋ Novo estacionamento"
            onPress={() => {
              setNovo({
                nome: "",
                endereco: "",
                andares: "2",
                vagas: "60",
                abertura: "06:00",
                fechamento: "23:00",
                taxa: "8",
              });
              setModal({ tipo: "novo" });
            }}
          />
        </View>
      ) : null}

      {estacionamentos.map((e) => {
        const pct =
          e.total_vagas > 0
            ? Math.round(((e.total_vagas - (e.vagas_disponiveis_total ?? 0)) / e.total_vagas) * 100)
            : 0;
        return (
          <Card key={e.id} className="p-4">
            <View className="flex-row flex-wrap items-center justify-between gap-3">
              <View className="flex-1" style={{ minWidth: 220 }}>
                <Text className="text-base font-bold text-slate-900">{e.nome}</Text>
                <Text className="mt-0.5 text-[13px] text-slate-500">{e.endereco}</Text>
                <Text className="mt-0.5 text-xs text-slate-400">
                  {e.total_andares} andares · {e.total_vagas} vagas ·{" "}
                  {e.hora_abertura}–{e.hora_fechamento} · {formatarMoedaBR(e.taxa_hora)}/h
                </Text>
                <View className="mt-3 flex-row items-center gap-3">
                  <View className="flex-1">
                    <BarraOcupacao percentual={pct} />
                  </View>
                  <Text className="text-[13px] font-extrabold" style={{ color: ocupacaoColor(pct) }}>
                    {pct}%
                  </Text>
                </View>
              </View>
              <View className="flex-row items-center gap-2 self-start">
                <Chip
                  label={`${e.vagas_disponiveis_total ?? 0} livres`}
                  tone={pct >= 90 ? "vermelho" : pct >= 70 ? "ambar" : "verde"}
                />
                <Botao label="Abrir mapa" variant="contorno" className="px-4 py-2" onPress={() => onAbrir(e.id)} />
              </View>
            </View>

            {podeGerenciar ? (
              <View className="mt-3 flex-row flex-wrap gap-2 border-t border-slate-100 pt-3">
                <Botao
                  label="＋ Andar"
                  variant="contorno"
                  className="px-3.5 py-1.5"
                  onPress={() => {
                    setAndarF({ numero: String(e.andares.length + 1), capacidade: "60" });
                    setModal({ tipo: "andar", est: e });
                  }}
                />
                <Botao
                  label="Vagas em lote"
                  variant="contorno"
                  className="px-3.5 py-1.5"
                  onPress={() => {
                    setLoteF({
                      andarId: e.andares[0]?.id ?? "",
                      quantidade: "40",
                      prefixo: "A",
                    });
                    setModal({ tipo: "vagas", est: e });
                  }}
                />
                <Botao
                  label="Excluir"
                  variant="contorno"
                  className="border-red-300 px-3.5 py-1.5"
                  onPress={() => excluir(e)}
                />
              </View>
            ) : null}
          </Card>
        );
      })}

      <ModalForma
        visivel={modal != null}
        titulo={
          modal?.tipo === "novo"
            ? "Novo estacionamento"
            : modal?.tipo === "andar"
              ? `Novo andar — ${modal.est.nome}`
              : "Gerar vagas em lote"
        }
        descricao={
          modal?.tipo === "novo"
            ? "Entra na rede imediatamente — depois cadastre andares e vagas."
            : modal?.tipo === "andar"
              ? "Andares negativos viram subsolo (ex.: -1 = G)."
              : "Cria vagas com códigos sequenciais (A01, A02…) no andar escolhido."
        }
        aoFechar={() => setModal(null)}
        aoConfirmar={salvar}
        ocupado={ocupado}
        rotuloConfirmar={modal?.tipo === "novo" ? "Criar estacionamento" : "Criar"}
      >
        {modal?.tipo === "novo" ? (
          <>
            <Campo label="Nome *" placeholder="Ex.: Shopping Via Norte" value={novo.nome} onChangeText={(v) => setNovo((f) => ({ ...f, nome: v }))} />
            <Campo label="Endereço" placeholder="Av. X, 123 - Bairro, Manaus/AM" value={novo.endereco} onChangeText={(v) => setNovo((f) => ({ ...f, endereco: v }))} />
            <View className="flex-row gap-3">
              <View className="flex-1">
                <Campo label="Nº de andares" keyboardType="numeric" value={novo.andares} onChangeText={(v) => setNovo((f) => ({ ...f, andares: v }))} />
              </View>
              <View className="flex-1">
                <Campo label="Vagas (total)" keyboardType="numeric" value={novo.vagas} onChangeText={(v) => setNovo((f) => ({ ...f, vagas: v }))} />
              </View>
            </View>
            <View className="flex-row gap-3">
              <View className="flex-1">
                <Campo label="Abre às" placeholder="06:00" value={novo.abertura} onChangeText={(v) => setNovo((f) => ({ ...f, abertura: v }))} />
              </View>
              <View className="flex-1">
                <Campo label="Fecha às" placeholder="23:00" value={novo.fechamento} onChangeText={(v) => setNovo((f) => ({ ...f, fechamento: v }))} />
              </View>
            </View>
            <Campo label="Taxa por hora (R$)" keyboardType="numeric" value={novo.taxa} onChangeText={(v) => setNovo((f) => ({ ...f, taxa: v }))} />
          </>
        ) : null}

        {modal?.tipo === "andar" ? (
          <>
            <Campo label="Número do andar" keyboardType="numbers-and-punctuation" helper="Use negativo para subsolo (-1 = G)" value={andarF.numero} onChangeText={(v) => setAndarF((f) => ({ ...f, numero: v }))} />
            <Campo label="Capacidade (vagas)" keyboardType="numeric" value={andarF.capacidade} onChangeText={(v) => setAndarF((f) => ({ ...f, capacidade: v }))} />
          </>
        ) : null}

        {modal?.tipo === "vagas" ? (
          <>
            {andaresDoLote.length === 0 ? (
              <Text className="mb-3 text-[13px] text-amber-700">
                Este estacionamento ainda não tem andares — crie um antes de gerar vagas.
              </Text>
            ) : (
              <View className="mb-1 flex-row flex-wrap gap-2">
                {andaresDoLote.map((a) => {
                  const ativo = a.id === loteF.andarId;
                  return (
                    <Pressable
                      key={a.id}
                      onPress={() => setLoteF((f) => ({ ...f, andarId: a.id }))}
                      className={`rounded-full border px-3.5 py-1.5 ${ativo ? "border-blue-600 bg-blue-50" : "border-slate-200 bg-white"}`}
                    >
                      <Text className={`text-[13px] font-semibold ${ativo ? "text-blue-700" : "text-slate-600"}`}>
                        {a.numero_andar}º andar
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
            )}
            <View className="flex-row gap-3">
              <View className="flex-1">
                <Campo label="Quantidade" keyboardType="numeric" value={loteF.quantidade} onChangeText={(v) => setLoteF((f) => ({ ...f, quantidade: v }))} />
              </View>
              <View className="flex-1">
                <Campo label="Prefixo dos códigos" autoCapitalize="characters" maxLength={2} value={loteF.prefixo} onChangeText={(v) => setLoteF((f) => ({ ...f, prefixo: v }))} />
              </View>
            </View>
          </>
        ) : null}
      </ModalForma>
    </View>
  );
}

// ==================================================== aba andares e vagas
function AbaAndares({
  estacionamentos,
  estSel,
}: {
  estacionamentos: Estacionamento[];
  estSel: string | null;
}) {
  const [est, setEst] = useState<string | null>(estSel);
  useEffect(() => setEst(estSel), [estSel]);
  const { mapa, loading } = useMapaVagas(est ?? undefined, {});
  const [andar, setAndar] = useState<number | null>(null);

  if (!est) {
    return (
      <Card className="p-8">
        <Text className="text-center text-sm text-slate-500">
          Selecione um estacionamento no topo para inspecionar andares e vagas.
        </Text>
      </Card>
    );
  }

  const andares = mapa ? [...mapa.andares].sort((a, b) => a.numero_andar - b.numero_andar) : [];
  const andarAtual = andares.find((a) => a.numero_andar === andar) ?? andares[0];
  const vagas = andarAtual
    ? mapa!.vagas.filter((v) => v.andar_id === andarAtual.id)
    : [];

  return (
    <Card className="p-5">
      <View className="mb-4 flex-row flex-wrap gap-2">
        {andares.map((a) => {
          const ativo = andarAtual?.id === a.id;
          return (
            <Pressable
              key={a.id}
              onPress={() => setAndar(a.numero_andar)}
              className={`rounded-full px-4 py-2 ${ativo ? "bg-blue-600" : "border border-slate-200 bg-white"}`}
            >
              <Text
                className={`text-[13px] font-semibold ${ativo ? "text-white" : "text-slate-600"}`}
              >
                {a.numero_andar}º andar
              </Text>
            </Pressable>
          );
        })}
        {loading && andares.length === 0 ? <ActivityIndicator color="#2563EB" /> : null}
      </View>
      <Text className="mb-3 text-[13px] text-slate-500">
        {andarAtual ? `${andarAtual.capacidade} vagas configuradas` : "—"}
      </Text>
      <VagaMapa vagas={vagas.slice(0, 96)} />
      {vagas.length > 96 ? (
        <Text className="mt-3 text-xs text-slate-400">
          + {vagas.length - 96} vagas não exibidas aqui — use o mapa completo.
        </Text>
      ) : null}
    </Card>
  );
}

// ==================================================== aba relatórios
function AbaRelatorios({ estSel }: { estSel: string | null }) {
  const [periodo, setPeriodo] = useState<"diario" | "semanal" | "mensal">("diario");
  const [dados, setDados] = useState<{
    total_entradas: number;
    total_saidas: number;
    tempo_medio_permanencia_min: number;
  } | null>(null);
  const [carregando, setCarregando] = useState(false);

  useEffect(() => {
    let alive = true;
    setCarregando(true);
    parkingApi
      .relatorioFluxo(periodo, estSel ?? undefined)
      .then((d) => alive && setDados(d))
      .catch(() => alive && setDados(null))
      .finally(() => alive && setCarregando(false));
    return () => {
      alive = false;
    };
  }, [periodo, estSel]);

  return (
    <View className="gap-5">
      <View className="flex-row gap-2">
        {(["diario", "semanal", "mensal"] as const).map((p) => (
          <Pressable
            key={p}
            onPress={() => setPeriodo(p)}
            className={`rounded-full px-4 py-2 ${
              periodo === p ? "bg-blue-600" : "border border-slate-200 bg-white"
            }`}
          >
            <Text
              className={`text-[13px] font-semibold capitalize ${
                periodo === p ? "text-white" : "text-slate-600"
              }`}
            >
              {p === "diario" ? "Diário" : p === "semanal" ? "Semanal" : "Mensal"}
            </Text>
          </Pressable>
        ))}
      </View>

      <View className="flex-row flex-wrap gap-3">
        <View className="min-w-[150px] flex-1">
          <StatTile rotulo="Entradas" valor={String(dados?.total_entradas ?? "—")} tone="verde" />
        </View>
        <View className="min-w-[150px] flex-1">
          <StatTile rotulo="Saídas" valor={String(dados?.total_saidas ?? "—")} tone="vermelho" />
        </View>
        <View className="min-w-[150px] flex-1">
          <StatTile
            rotulo="Permanência média"
            valor={formatarMinutos(dados?.tempo_medio_permanencia_min)}
            tone="roxo"
          />
        </View>
      </View>
      {carregando ? <ActivityIndicator color="#2563EB" /> : null}
      <Text className="text-xs text-slate-400">
        Relatório consolidado de entradas e saídas no período — fonte dos dados
        históricos do estacionamento.
      </Text>
    </View>
  );
}

// ==================================================== aba usuários
function AbaUsuarios({
  isAdmin,
  estacionamentos,
}: {
  isAdmin: boolean;
  estacionamentos: Estacionamento[];
  onChanged?: () => void;
}) {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [modal, setModal] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [f, setF] = useState({
    nome: "",
    email: "",
    senha: "",
    role: "usuario" as "usuario" | "gestor" | "financeiro" | "admin",
    estacionamento_id: null as string | null,
  });

  const carregar = useCallback(async () => {
    try {
      setUsuarios(await parkingApi.listarUsuarios());
      setErro(null);
    } catch (e) {
      setErro(apiErrorMessage(e, "Rota disponível apenas para administradores."));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    if (isAdmin) carregar();
    else setCarregando(false);
  }, [isAdmin, carregar]);

  if (!isAdmin) {
    return (
      <Card className="p-8">
        <Text className="text-center text-sm text-slate-500">
          Gestão de usuários é exclusiva do administrador global.
        </Text>
      </Card>
    );
  }

  const exigeVinculo = f.role === "gestor" || f.role === "financeiro";

  async function criar() {
    if (f.nome.trim().length < 2 || !f.email.includes("@") || f.senha.length < 6) {
      Alert.alert("Confira os campos", "Nome (mín. 2), e-mail válido e senha com 6+ caracteres.");
      return;
    }
    if (exigeVinculo && !f.estacionamento_id) {
      Alert.alert("Vínculo obrigatório", "gestor e financeiro precisam estar ligados a um estacionamento.");
      return;
    }
    setOcupado(true);
    try {
      const novo = await parkingApi.criarUsuario({
        nome: f.nome.trim(),
        email: f.email.trim().toLowerCase(),
        senha: f.senha,
        role: f.role,
        estacionamento_id: exigeVinculo ? (f.estacionamento_id ?? undefined) : undefined,
      });
      setUsuarios((prev) => [novo, ...prev]);
      setModal(false);
      setF({ nome: "", email: "", senha: "", role: "usuario", estacionamento_id: null });
      Alert.alert("Usuário criado ✅", `${novo.nome} já pode entrar com a senha cadastrada.`);
    } catch (e) {
      Alert.alert("Não foi possível criar", apiErrorMessage(e));
    } finally {
      setOcupado(false);
    }
  }

  async function alternar(u: Usuario) {
    try {
      const novo = await parkingApi.alternarUsuario(u.id);
      setUsuarios((prev) => prev.map((x) => (x.id === novo.id ? novo : x)));
    } catch (e) {
      setErro(apiErrorMessage(e));
    }
  }

  return (
    <View className="gap-3">
      <View className="flex-row items-center justify-between">
        <Text className="text-sm text-slate-500">
          {usuarios.length} conta(s) · níveis controlam o que cada um vê no painel
        </Text>
        <Botao label="＋ Novo usuário" onPress={() => setModal(true)} />
      </View>

      {erro ? (
        <View className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <Text className="text-[13px] text-amber-700">⚠️ {erro}</Text>
        </View>
      ) : null}
      {carregando ? <BlocoCentral /> : null}
      {usuarios.map((u) => (
        <Card key={u.id} className="flex-row flex-wrap items-center gap-3 p-4">
          <View className="h-9 w-9 items-center justify-center rounded-full bg-blue-100">
            <Text className="text-[13px] font-bold text-blue-700">
              {u.nome.slice(0, 1).toUpperCase()}
            </Text>
          </View>
          <View className="min-w-[160px] flex-1">
            <Text className="text-sm font-bold text-slate-900">{u.nome}</Text>
            <Text className="text-xs text-slate-500">{u.email}</Text>
          </View>
          <Chip
            label={ROLE_LABEL[u.role] ?? u.role}
            tone={u.role === "admin" ? "vermelho" : u.role === "usuario" ? "neutro" : "azul"}
          />
          {u.placa_veiculo ? <Chip label={u.placa_veiculo} tone="vaga" /> : null}
          <Botao
            label={u.is_ativo ? "Desativar" : "Reativar"}
            variant="contorno"
            className={`px-4 py-2 ${u.is_ativo ? "border-red-300" : "border-emerald-300"}`}
            onPress={() => alternar(u)}
          />
        </Card>
      ))}

      <ModalForma
        visivel={modal}
        titulo="Novo usuário"
        descricao="A senha é armazenada com bcrypt; o primeiro login já funciona."
        aoFechar={() => setModal(false)}
        aoConfirmar={criar}
        ocupado={ocupado}
        rotuloConfirmar="Criar usuário"
      >
        <Campo label="Nome completo *" value={f.nome} onChangeText={(v) => setF((p) => ({ ...p, nome: v }))} autoCapitalize="words" />
        <Campo label="E-mail *" placeholder="pessoa@empresa.com" value={f.email} onChangeText={(v) => setF((p) => ({ ...p, email: v }))} autoCapitalize="none" keyboardType="email-address" />
        <Campo label="Senha *" senha value={f.senha} onChangeText={(v) => setF((p) => ({ ...p, senha: v }))} />
        <Text className="mb-1.5 mt-1 text-xs font-semibold text-slate-500">Nível de acesso</Text>
        <View className="mb-3 flex-row flex-wrap gap-2">
          {(
            [
              ["usuario", "🚗 Motorista"],
              ["gestor", "🏬 Gestor de shopping"],
              ["financeiro", "💰 Financeiro"],
              ["admin", "👑 Admin global"],
            ] as const
          ).map(([role, label]) => {
            const ativo = f.role === role;
            return (
              <Pressable
                key={role}
                onPress={() => setF((p) => ({ ...p, role }))}
                className={`rounded-full border px-3.5 py-1.5 ${ativo ? "border-blue-600 bg-blue-50" : "border-slate-200 bg-white"}`}
              >
                <Text className={`text-[12px] font-semibold ${ativo ? "text-blue-700" : "text-slate-500"}`}>
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>
        {exigeVinculo ? (
          <>
            <Text className="mb-1.5 text-xs font-semibold text-slate-500">
              Estacionamento vinculado * (painel limitado a ele)
            </Text>
            <View className="mb-2 flex-row flex-wrap gap-2">
              {estacionamentos.map((e) => {
                const ativo = e.id === f.estacionamento_id;
                return (
                  <Pressable
                    key={e.id}
                    onPress={() => setF((p) => ({ ...p, estacionamento_id: e.id }))}
                    className={`rounded-full border px-3.5 py-1.5 ${ativo ? "border-blue-600 bg-blue-50" : "border-slate-200 bg-white"}`}
                  >
                    <Text className={`text-[12px] font-semibold ${ativo ? "text-blue-700" : "text-slate-500"}`}>
                      {e.nome}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          </>
        ) : null}
      </ModalForma>
    </View>
  );
}

function BlocoCentral() {
  return (
    <View className="py-8">
      <ActivityIndicator size="large" color="#2563EB" />
    </View>
  );
}
