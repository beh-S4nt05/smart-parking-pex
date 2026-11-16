import { useEffect, useState } from "react";
import { Platform, Pressable, Text, View } from "react-native";
import { parkingApi, apiErrorMessage } from "../services/api";

type Sessao = {
  id: string;
  dispositivo: string;
  criado_em: string;
  expira_em: string;
  ativa: boolean;
};

export default function SessoesAtivas({ onRevogarTodas }: { onRevogarTodas: () => Promise<void> }) {
  const [sessoes, setSessoes] = useState<Sessao[]>([]);
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState(false);

  async function atualizar() {
    try {
      const lista = await parkingApi.listarSessoes();
      setSessoes(lista);
      setErro("");
    } catch (e) {
      setErro(apiErrorMessage(e, "Não foi possível listar as sessões"));
    }
  }

  useEffect(() => { void atualizar(); }, []);
  async function revogar(id: string) {
    setOcupado(true);
    try {
      await parkingApi.revogarSessao(id);
      await atualizar();
    } catch (e) { setErro(apiErrorMessage(e)); }
    finally { setOcupado(false); }
  }

  async function todas() {
    const continuar = Platform.OS !== "web" || typeof window === "undefined" ||
      window.confirm("Encerrar todas as sessões, inclusive esta?");
    if (!continuar) return;
    setOcupado(true);
    try { await parkingApi.revogarTodasSessoes(); await onRevogarTodas(); }
    catch (e) { setErro(apiErrorMessage(e)); }
    finally { setOcupado(false); }
  }

  return (
    <View style={{ backgroundColor: "#FFFFFF", borderRadius: 18, padding: 18, gap: 12 }}>
      <Text style={{ fontSize: 16, fontWeight: "800", color: "#15233B" }}>Dispositivos e sessões</Text>
      <Text style={{ fontSize: 12, lineHeight: 18, color: "#475569" }}>
        Consulte os dispositivos autorizados e encerre sessões que não reconhecer.
      </Text>
      {erro ? <Text accessibilityRole="alert" style={{ color: "#B91C1C" }}>{erro}</Text> : null}
      {sessoes.length === 0 ? <Text style={{ color: "#475569" }}>Nenhuma sessão listada.</Text> : null}
      {sessoes.map(s => (
        <View key={s.id} style={{ borderWidth: 1, borderColor: "#E2E8F0", borderRadius: 12, padding: 12, gap: 8 }}>
          <Text style={{ color: "#0F172A", fontWeight: "700" }}>{s.dispositivo}</Text>
          <Text style={{ color: "#475569", fontSize: 12 }}>
            {s.ativa ? "Ativa" : "Revogada/expirada"} · {new Date(s.criado_em).toLocaleDateString("pt-BR")}
          </Text>
          {s.ativa ? (
            <Pressable accessibilityRole="button" disabled={ocupado} onPress={() => void revogar(s.id)}
              style={{ minHeight: 44, backgroundColor: "#FEE2E2", padding: 12, borderRadius: 12, alignSelf: "flex-start" }}>
              <Text style={{ fontWeight: "800", color: "#B91C1C" }}>Encerrar esta sessão</Text>
            </Pressable>
          ) : null}
        </View>
      ))}
      <Pressable accessibilityRole="button" disabled={ocupado} onPress={() => void atualizar()}
        style={{ minHeight: 44, padding: 12, backgroundColor: "#EFF6FF", borderRadius: 12 }}>
        <Text style={{ fontWeight: "800", color: "#1D4ED8", textAlign: "center" }}>Atualizar sessões</Text>
      </Pressable>
      <Pressable accessibilityRole="button" disabled={ocupado} onPress={() => void todas()}
        style={{ minHeight: 44, padding: 12, backgroundColor: "#FEE2E2", borderRadius: 12 }}>
        <Text style={{ fontWeight: "800", color: "#B91C1C", textAlign: "center" }}>Sair de todos os dispositivos</Text>
      </Pressable>
    </View>
  );
}
