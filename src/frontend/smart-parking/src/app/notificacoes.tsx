/** Central interna da V1 — dados autorizados pelo JWT, sem dependência do push remoto. */
import { useCallback, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Switch, Text, View } from "react-native";
import { useFocusEffect, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import Header from "../components/Header";
import { MobileScreenHeader } from "../components/MobileChrome";
import { useAuth } from "../hooks/useAuth";
import { useNotificacoes } from "../components/Notificacoes";
import { apiErrorMessage } from "../services/api";
import {
  notificacoesApi, type AcompanhamentoV1, type NotificacaoV1,
  type PreferenciasNotificacaoV1,
} from "../services/notificacoesApi";

function destinoSeguro(destino: string | null): string | null {
  if (!destino) return null;
  if (destino === "/reservas" || destino === "/dashboard" || destino === "/perfil") return destino;
  if (/^\/shopping\/[a-zA-Z0-9_-]+$/.test(destino)) return destino;
  return null;
}
const C = { azul: "#2563EB", texto: "#0F172A", cinza: "#64748B", borda: "#E2E8F0" };
const TITULOS = [
  ["reservas", "Reservas, cancelamentos e expirações"],
  ["lembretes", "Lembretes antes de vencer"],
  ["vagas", "Vagas que estou acompanhando"],
  ["financeiro", "Pagamentos e fechamento de caixa"],
  ["resumo_diario", "Resumo financeiro diário"],
] as const;

export default function TelaNotificacoes() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { avisar } = useNotificacoes();
  const [notificacoes, setNotificacoes] = useState<NotificacaoV1[]>([]);
  const [preferencias, setPreferencias] = useState<PreferenciasNotificacaoV1 | null>(null);
  const [acompanhamentos, setAcompanhamentos] = useState<AcompanhamentoV1[]>([]);
  const [filtro, setFiltro] = useState<"todas" | "nao_lidas">("todas");
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [mais, setMais] = useState(false);

  const atualizar = useCallback(async (silencioso = false) => {
    if (!user) return;
    if (!silencioso) setCarregando(true);
    try {
      const [lista, pref, watches] = await Promise.all([
        notificacoesApi.listar(filtro),
        notificacoesApi.preferencias(),
        notificacoesApi.acompanhamentos(),
      ]);
      setNotificacoes(lista);
      setMais(lista.length === 30);
      setPreferencias(pref);
      setAcompanhamentos(watches);
      setErro(null);
    } catch (e) {
      if (!silencioso) setErro(apiErrorMessage(e, "Não foi possível carregar notificações."));
    } finally {
      if (!silencioso) setCarregando(false);
    }
  }, [user?.id, filtro]);

  useFocusEffect(useCallback(() => {
    if (!user) return;
    void atualizar();
    const timer = setInterval(() => void atualizar(true), 15000);
    return () => clearInterval(timer);
  }, [user?.id, atualizar]));

  async function abrir(n: NotificacaoV1) {
    try {
      await notificacoesApi.ler(n.id);
      setNotificacoes(atual => atual.map(i => i.id === n.id ? { ...i, lida_em: new Date().toISOString() } : i));
    } catch (e) {
      avisar("Não foi possível marcar como lida", apiErrorMessage(e), "erro");
    }
    const rota = destinoSeguro(n.destino);
    if (rota) router.push(rota as never);
  }

  async function atualizarOpcao(chave: keyof PreferenciasNotificacaoV1, ativo: boolean) {
    if (!preferencias || salvando) return;
    const anterior = preferencias;
    const proxima = { ...preferencias, [chave]: ativo };
    setPreferencias(proxima);
    setSalvando(true);
    try {
      await notificacoesApi.salvarPreferencias(proxima);
    } catch (e) {
      setPreferencias(anterior);
      avisar("Erro ao salvar preferência", apiErrorMessage(e), "erro");
    } finally { setSalvando(false); }
  }

  async function carregarMais() {
    try {
      const page = await notificacoesApi.listar(filtro, notificacoes.length);
      setNotificacoes(anteriores => {
        const ids = new Set(anteriores.map(n => n.id));
        return [...anteriores, ...page.filter(n => !ids.has(n.id))];
      });
      setMais(page.length === 30);
    } catch (e) { avisar("Falha ao carregar", apiErrorMessage(e), "erro"); }
  }

  async function pararAcompanhamento(id: string) {
    try {
      await notificacoesApi.pararAcompanhamento(id);
      setAcompanhamentos(a => a.filter(w => w.id !== id));
      avisar("Acompanhamento encerrado", undefined, "sucesso");
    } catch (e) { avisar("Falha ao encerrar acompanhamento", apiErrorMessage(e), "erro"); }
  }

  return (
    <View style={{ flex: 1, backgroundColor: "#F8FAFC" }}>
      <Header rotaAtual="/notificacoes" />
      <MobileScreenHeader title="Notificações" subtitle="Vagas, reservas e movimentações da sua conta" />
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 50, maxWidth: 760, width: "100%", alignSelf: "center" }}>
        {authLoading ? <ActivityIndicator /> : !user ? (
          <View style={{ padding: 20, backgroundColor: "#fff", borderRadius: 16 }}>
            <Text style={{ fontWeight: "700", color: C.texto }}>Entre na sua conta para ver notificações.</Text>
            <Pressable onPress={() => router.push("/login")} style={{ marginTop: 14 }}>
              <Text style={{ color: C.azul, fontWeight: "700" }}>Ir para login</Text>
            </Pressable>
          </View>
        ) : (
          <>
            <View style={{ backgroundColor: "#fff", padding: 16, borderRadius: 16, marginBottom: 14 }}>
              <Text style={{ fontSize: 16, fontWeight: "800", color: C.texto }}>Central de notificações</Text>
              <Text style={{ color: C.cinza, marginTop: 4, fontSize: 12 }}>Avisos registrados pelo servidor permanecem disponíveis mesmo sem push.</Text>
              <View style={{ flexDirection: "row", gap: 16, marginTop: 15, alignItems: "center" }}>
                {(["todas", "nao_lidas"] as const).map(f => (
                  <Pressable key={f} accessibilityRole="button" accessibilityLabel={f === "todas" ? "Todas" : "Não lidas"} onPress={() => setFiltro(f)}>
                    <Text style={{ color: filtro === f ? C.azul : C.cinza, fontWeight: "700" }}>{f === "todas" ? "Todas" : "Não lidas"}</Text>
                  </Pressable>
                ))}
                <Pressable onPress={async () => {
                  try { await notificacoesApi.lerTodas(); await atualizar(true); }
                  catch (e) { avisar("Falha ao marcar notificações", apiErrorMessage(e), "erro"); }
                }} style={{ marginLeft: "auto" }}>
                  <Text style={{ color: C.azul, fontSize: 12, fontWeight: "700" }}>Marcar todas como lidas</Text>
                </Pressable>
              </View>
              {carregando ? <ActivityIndicator style={{ marginTop: 18 }} /> : erro ? (
                <Text style={{ color: "#B91C1C", marginTop: 12 }}>{erro}</Text>
              ) : notificacoes.length === 0 ? (
                <Text style={{ color: C.cinza, marginTop: 16 }}>Nenhuma notificação no momento.</Text>
              ) : notificacoes.map(n => (
                <Pressable key={n.id} onPress={() => void abrir(n)} accessibilityRole="button"
                  style={{ paddingVertical: 13, paddingHorizontal: 6, borderBottomWidth: 1, borderColor: C.borda, backgroundColor: n.lida_em ? "#fff" : "#EFF6FF" }}>
                  <View style={{ flexDirection: "row", gap: 9, alignItems: "center" }}>
                    <Ionicons name={n.lida_em ? "notifications-outline" : "notifications"} size={18} color={C.azul} />
                    <Text style={{ fontWeight: "800", color: C.texto, flex: 1 }}>{n.titulo}</Text>
                  </View>
                  <Text style={{ color: C.cinza, fontSize: 12, marginTop: 4, marginLeft: 27 }}>{n.mensagem}</Text>
                  <Text style={{ color: C.cinza, fontSize: 10, marginTop: 5, marginLeft: 27 }}>{new Date(n.criada_em).toLocaleString("pt-BR")}</Text>
                </Pressable>
              ))}
              {mais ? (
                <Pressable onPress={() => void carregarMais()} style={{ padding: 10, alignItems: "center" }}>
                  <Text style={{ color: C.azul, fontWeight: "700" }}>Carregar mais</Text>
                </Pressable>
              ) : null}
            </View>
            <View style={{ backgroundColor: "#fff", padding: 16, borderRadius: 16, marginBottom: 14 }}>
              <Text style={{ fontSize: 16, fontWeight: "800", color: C.texto }}>Preferências</Text>
              <Text style={{ color: C.cinza, fontSize: 12, marginTop: 3 }}>As notificações externas precisam de permissão do celular.</Text>
              {preferencias ? (
                <>
                  {TITULOS.map(([chave, rotulo]) => (
                    <View key={chave} style={{ flexDirection: "row", alignItems: "center", paddingVertical: 9, borderBottomWidth: 1, borderColor: C.borda, gap: 10 }}>
                      <Text style={{ flex: 1, color: C.texto, fontSize: 13 }}>{rotulo}</Text>
                      <Switch accessibilityLabel={rotulo} value={Boolean(preferencias[chave])} onValueChange={v => void atualizarOpcao(chave, v)} disabled={salvando} />
                    </View>
                  ))}
                  <Text style={{ color: C.cinza, marginTop: 9, fontSize: 11 }}>Push remoto requer um aplicativo instalado com credenciais Android/iOS. O recebimento não é garantido pelo provedor.</Text>
                </>
              ) : null}
            </View>
            <View style={{ backgroundColor: "#fff", padding: 16, borderRadius: 16 }}>
              <Text style={{ color: C.texto, fontWeight: "800", fontSize: 16 }}>Vagas acompanhadas</Text>
              <Text style={{ color: C.cinza, fontSize: 12, marginTop: 3 }}>Escolha um estacionamento no mapa para ativar avisos de disponibilidade.</Text>
              {acompanhamentos.map(w => (
                <View key={w.id} style={{ flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: 10 }}>
                  <Text style={{ flex: 1, color: C.texto }}>Estacionamento {w.estacionamento_id.slice(0, 8)} · {w.tipo_vaga}</Text>
                  <Pressable onPress={() => void pararAcompanhamento(w.id)} accessibilityRole="button" accessibilityLabel="Parar acompanhamento">
                    <Text style={{ color: "#B91C1C", fontSize: 12, fontWeight: "700" }}>Parar</Text>
                  </Pressable>
                </View>
              ))}
            </View>
          </>
        )}
      </ScrollView>
    </View>
  );
}
