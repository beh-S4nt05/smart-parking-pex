import { useCallback, useEffect, useState } from "react";
import { Alert, Platform, Pressable, Text, View } from "react-native";
import { Botao, Campo } from "./ui";
import { apiErrorMessage, parkingApi } from "../services/api";

type Pedido = { id: string; usuario_id: string; usuario_nome: string; tipo: "idoso" | "pcd"; status: string };

function avisar(t: string, msg: string) {
  if (Platform.OS === "web") window.alert(`${t}\n${msg}`);
  else Alert.alert(t, msg);
}

export default function AnaliseCredenciaisAdmin() {
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const [referencia, setReferencia] = useState("");
  const [justificativa, setJustificativa] = useState("");
  const [salvando, setSalvando] = useState(false);

  const carregar = useCallback(async () => {
    try {
      setPedidos(await parkingApi.credenciaisPendentesAdmin());
      setErro(null);
    } catch (e) {
      setErro(apiErrorMessage(e));
    }
  }, []);
  useEffect(() => { void carregar(); }, [carregar]);

  async function avaliar(decisao: "aprovado" | "rejeitado") {
    if (justificativa.trim().length < 8) {
      avisar("Justificativa necessária", "Registre ao menos 8 caracteres para auditoria.");
      return;
    }
    if (decisao === "aprovado" && referencia.trim().length < 4) {
      avisar("Credencial necessária", "Confira a credencial oficial e informe sua referência.");
      return;
    }
    if (!selecionado) return;
    setSalvando(true);
    try {
      await parkingApi.avaliarCredencialAdmin(selecionado, {
        decisao,
        justificativa: justificativa.trim(),
        metodo_verificacao: "conferencia_presencial",
        referencia_oficial: referencia.trim() || undefined,
      });
      setSelecionado(null);
      setReferencia("");
      setJustificativa("");
      await carregar();
      avisar("Análise registrada", `Credencial ${decisao === "aprovado" ? "aprovada" : "rejeitada"} com auditoria.`);
    } catch (e) {
      avisar("Erro ao avaliar", apiErrorMessage(e));
    } finally { setSalvando(false); }
  }

  return (
    <View style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 20, gap: 13 }}>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
        <View style={{ flex: 1 }}>
          <Text style={{ fontSize: 18, fontWeight: "800", color: "#15233B" }}>Credenciais pendentes</Text>
          <Text style={{ fontSize: 12, color: "#64748B", marginTop: 4 }}>Acesso administrativo: validação com evidência oficial</Text>
        </View>
        <Pressable onPress={() => void carregar()} accessibilityRole="button"
          style={{ backgroundColor: "#EAF1FF", padding: 11, borderRadius: 12, minHeight: 44, justifyContent: "center" }}>
          <Text style={{ color: "#1D4ED8", fontWeight: "800", fontSize: 12 }}>Atualizar</Text>
        </Pressable>
      </View>
      {erro ? <Text style={{ color: "#BE123C" }}>{erro}</Text> : null}
      {pedidos.length === 0 ? <Text style={{ color: "#64748B" }}>Não há solicitações pendentes.</Text> : null}
      {pedidos.map((p) => (
        <View key={p.id} style={{ backgroundColor: "#F3F7FD", padding: 13, borderRadius: 14, gap: 10 }}>
          <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
            <View style={{ flex: 1 }}>
              <Text style={{ fontSize: 14, fontWeight: "800", color: "#15233B" }}>{p.usuario_nome}</Text>
              <Text style={{ fontSize: 12, color: "#475569", marginTop: 3 }}>Solicitação {p.tipo.toUpperCase()} · pendente</Text>
            </View>
            <Pressable onPress={() => setSelecionado((cur) => cur === p.id ? null : p.id)}
              accessibilityRole="button" style={{ backgroundColor: "#DBEAFE", borderRadius: 11, padding: 12, minHeight: 44 }}>
              <Text style={{ color: "#1D4ED8", fontSize: 12, fontWeight: "800" }}>
                {selecionado === p.id ? "Fechar" : "Analisar"}
              </Text>
            </Pressable>
          </View>
          {selecionado === p.id ? (
            <View style={{ paddingTop: 9, borderTopWidth: 1, borderColor: "#E2E8F0" }}>
              <Text style={{ color: "#64748B", fontSize: 12, lineHeight: 18, marginBottom: 12 }}>
                Confira o documento/credencial por procedimento oficial. A referência será armazenada somente como hash.
              </Text>
              <Campo label="Referência oficial conferida" placeholder="Número ou referência verificada"
                value={referencia} onChangeText={setReferencia} />
              <Campo label="Justificativa da análise" placeholder="Descreva o método e o resultado" value={justificativa}
                onChangeText={setJustificativa} />
              <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 9 }}>
                <Botao label="Aprovar credencial" onPress={() => void avaliar("aprovado")} loading={salvando} />
                <Botao label="Rejeitar" variant="contorno" onPress={() => void avaliar("rejeitado")} disabled={salvando} />
              </View>
            </View>
          ) : null}
        </View>
      ))}
    </View>
  );
}
