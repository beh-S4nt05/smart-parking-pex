import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Alert, Platform, Pressable, Text, View } from "react-native";
import { Botao, Campo } from "./ui";
import OptionChips from "./OptionChips";
import { parkingApi, apiErrorMessage } from "../services/api";
import type { CategoriaVeiculo, CredencialUsuario, MotorizacaoVeiculo, VeiculoUsuario } from "../types/api";

const normalizarPlaca = (v: string) => v.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 7);
const titulo = { fontSize: 18, fontWeight: "800" as const, color: "#15233B" };

function avisar(t: string, mensagem: string) {
  if (Platform.OS === "web") {
    window.alert(`${t}\n\n${mensagem}`);
  } else {
    Alert.alert(t, mensagem);
  }
}

function converterData(data: string): string | null {
  if (!/^[0-9]{2}\/[0-9]{2}\/[0-9]{4}$/.test(data)) return null;
  const [d, m, a] = data.split("/").map(Number);
  const teste = new Date(Date.UTC(a, m - 1, d));
  if (teste.getUTCFullYear() !== a || teste.getUTCMonth() !== m - 1 || teste.getUTCDate() !== d) return null;
  if (teste > new Date()) return null;
  return `${String(a).padStart(4, "0")}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

const ESTADOS: Record<string, string> = {
  pendente: "Aguardando análise",
  aprovado: "Credencial validada",
  rejeitado: "Verificação rejeitada",
  expirado: "Credencial vencida",
  revogado: "Credencial revogada",
};

export default function GaragemECredenciais({
  dataNascimento,
  onProfileChanged,
}: {
  dataNascimento?: string | null;
  onProfileChanged: () => Promise<void>;
}) {
  const [veiculos, setVeiculos] = useState<VeiculoUsuario[]>([]);
  const [credenciais, setCredenciais] = useState<CredencialUsuario[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [exibirFormulario, setExibirFormulario] = useState(false);
  const [placa, setPlaca] = useState("");
  const [modelo, setModelo] = useState("");
  const [categoria, setCategoria] = useState<CategoriaVeiculo>("carro");
  const [motorizacao, setMotorizacao] = useState<MotorizacaoVeiculo>("combustao");
  const [nascimento, setNascimento] = useState(dataNascimento ? dataNascimento.split("-").reverse().join("/") : "");

  useEffect(() => {
    setNascimento(dataNascimento ? dataNascimento.split("-").reverse().join("/") : "");
  }, [dataNascimento]);

  const recarregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const [v, creds] = await Promise.all([parkingApi.listarVeiculos(), parkingApi.listarCredenciais()]);
      setVeiculos(v);
      setCredenciais(creds);
    } catch (e) {
      setErro(apiErrorMessage(e, "Não foi possível carregar veículos e credenciais."));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => { void recarregar(); }, [recarregar]);

  async function adicionar() {
    if (!/^[A-Z]{3}[0-9]{4}$/.test(placa) && !/^[A-Z]{3}[0-9][A-Z][0-9]{2}$/.test(placa)) {
      avisar("Placa inválida", "Informe uma placa como ABC1234 ou ABC1D23.");
      return;
    }
    setSalvando(true);
    try {
      await parkingApi.criarVeiculo({ placa, modelo: modelo.trim() || undefined, categoria, motorizacao });
      setPlaca(""); setModelo(""); setExibirFormulario(false);
      await recarregar();
    } catch (e) {
      avisar("Não foi possível cadastrar", apiErrorMessage(e));
    } finally { setSalvando(false); }
  }

  async function remover(v: VeiculoUsuario) {
    async function executar() {
      setSalvando(true);
      try { await parkingApi.removerVeiculo(v.id); await recarregar(); }
      catch (e) { avisar("Não foi possível remover", apiErrorMessage(e)); }
      finally { setSalvando(false); }
    }
    if (Platform.OS === "web") {
      if (window.confirm(`Remover o veículo ${v.placa}?`)) void executar();
    } else {
      Alert.alert("Remover veículo", `Remover ${v.placa} da sua garagem?`, [
        { text: "Cancelar", style: "cancel" },
        { text: "Remover", style: "destructive", onPress: () => { void executar(); } },
      ]);
    }
  }

  async function solicitar(tipo: "idoso" | "pcd") {
    setSalvando(true);
    try {
      if (tipo === "idoso" && !dataNascimento) {
        const iso = converterData(nascimento);
        if (!iso) {
          avisar("Confira a data", "Informe a data de nascimento válida no formato DD/MM/AAAA.");
          return;
        }
        await parkingApi.atualizarMe({ data_nascimento: iso });
        await onProfileChanged();
      }
      await parkingApi.solicitarCredencial(tipo);
      await recarregar();
      avisar("Solicitação registrada", "Sua credencial ficará pendente até a conferência por um responsável autorizado. Não há liberação automática de vagas.");
    } catch (e) {
      avisar("Não foi possível solicitar", apiErrorMessage(e));
    } finally { setSalvando(false); }
  }

  if (carregando && veiculos.length === 0 && credenciais.length === 0) {
    return <View style={{ padding: 18, alignItems: "center" }}><ActivityIndicator color="#2563EB" /></View>;
  }

  return (
    <View style={{ gap: 16 }}>
      <View style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 20, gap: 13 }}>
        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
          <View style={{ flex: 1 }}>
            <Text style={titulo}>Meus veículos</Text>
            <Text style={{ fontSize: 12, color: "#64748B", marginTop: 4 }}>Carros, motos e modelos elétricos</Text>
          </View>
          <Pressable accessibilityRole="button" onPress={() => setExibirFormulario((v) => !v)}
            style={{ paddingVertical: 11, paddingHorizontal: 14, borderRadius: 13, backgroundColor: "#EAF1FF", minHeight: 44 }}>
            <Text style={{ color: "#1D4ED8", fontWeight: "800", fontSize: 13 }}>{exibirFormulario ? "Fechar" : "+ Adicionar"}</Text>
          </Pressable>
        </View>
        {veiculos.length === 0 && !exibirFormulario ? (
          <Text style={{ color: "#64748B", fontSize: 13 }}>Ainda não há veículos. Você pode adicioná-los quando quiser.</Text>
        ) : null}
        {veiculos.map((v) => (
          <View key={v.id} style={{ backgroundColor: "#F4F7FD", borderRadius: 13, padding: 13, flexDirection: "row", alignItems: "center", gap: 8 }}>
            <View style={{ flex: 1 }}>
              <Text style={{ color: "#15233B", fontSize: 15, fontWeight: "800" }}>{v.placa} {v.principal ? "· Principal" : ""}</Text>
              <Text style={{ color: "#64748B", fontSize: 12, marginTop: 3 }}>
                {v.categoria === "moto" ? "Moto" : "Carro"} · {v.motorizacao === "eletrico" ? "Elétrico" : v.motorizacao === "hibrido" ? "Híbrido" : v.motorizacao === "combustao" ? "Combustão" : "Não informada"}
                {v.modelo ? ` · ${v.modelo}` : ""}
              </Text>
            </View>
            <Pressable disabled={salvando} onPress={() => void remover(v)} accessibilityRole="button"
              accessibilityLabel={`Remover veículo ${v.placa}`}
              style={{ padding: 10, borderRadius: 10, backgroundColor: "#FFE8E8", minHeight: 44, justifyContent: "center" }}>
              <Text style={{ color: "#B91C1C", fontSize: 12, fontWeight: "800" }}>Remover</Text>
            </Pressable>
          </View>
        ))}
        {exibirFormulario ? (
          <View style={{ borderTopWidth: 1, borderColor: "#E5EAF2", paddingTop: 16 }}>
            <OptionChips label="Veículo" value={categoria} onChange={setCategoria} options={[{ value: "carro", label: "Carro" }, { value: "moto", label: "Moto" }]} />
            <OptionChips label="Motorização" value={motorizacao} onChange={setMotorizacao}
              options={[{ value: "combustao", label: "Combustão" }, { value: "hibrido", label: "Híbrido" }, { value: "eletrico", label: "Elétrico" }]} />
            <Campo label="Placa" placeholder="ABC1D23" autoCapitalize="characters" maxLength={7}
              value={placa} onChangeText={(v) => setPlaca(normalizarPlaca(v))} />
            <Campo label="Modelo" placeholder="Opcional" value={modelo} onChangeText={setModelo} opcional />
            <Botao label="Salvar veículo" onPress={() => void adicionar()} loading={salvando} />
          </View>
        ) : null}
      </View>

      <View style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 20, gap: 11 }}>
        <Text style={titulo}>Vagas especiais</Text>
        <Text style={{ fontSize: 13, color: "#64748B", lineHeight: 20 }}>
          Idoso (60+) e PCD: a liberação depende de credencial oficial conferida. Você pode continuar reservando vagas comuns enquanto aguarda.
        </Text>
        {credenciais.map((cred) => (
          <View key={cred.id} style={{ borderRadius: 12, padding: 12, backgroundColor: "#F4F7FD", flexDirection: "row", justifyContent: "space-between", gap: 8 }}>
            <Text style={{ fontWeight: "800", color: "#15233B" }}>{cred.tipo === "idoso" ? "Idoso" : "PCD"}</Text>
            <Text style={{ color: cred.status === "aprovado" ? "#047857" : "#8A5A19", fontWeight: "700", fontSize: 12 }}>
              {ESTADOS[cred.status] ?? cred.status}
            </Text>
          </View>
        ))}
        {dataNascimento ? (
          <Text style={{ fontSize: 12, color: "#64748B" }}>Nascimento cadastrado: {dataNascimento.split("-").reverse().join("/")}</Text>
        ) : (
          <Campo label="Nascimento (para solicitação de idoso)" placeholder="DD/MM/AAAA" keyboardType="numeric"
            value={nascimento} onChangeText={(v) => {
              const n = v.replace(/\D/g, "").slice(0, 8);
              setNascimento(n.length <= 2 ? n : n.length <= 4 ? `${n.slice(0, 2)}/${n.slice(2)}` : `${n.slice(0, 2)}/${n.slice(2, 4)}/${n.slice(4)}`);
            }} />
        )}
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {(["idoso", "pcd"] as const).map((tipo) => {
            const bloqueado = credenciais.some((c) => c.tipo === tipo && ["pendente", "aprovado"].includes(c.status));
            return (
              <Pressable key={tipo} accessibilityRole="button" disabled={salvando || bloqueado}
                onPress={() => void solicitar(tipo)}
                style={{ padding: 13, minHeight: 44, borderRadius: 12, backgroundColor: bloqueado ? "#E8EDF4" : "#EAF1FF", opacity: bloqueado ? 0.7 : 1 }}>
                <Text style={{ color: bloqueado ? "#64748B" : "#1D4ED8", fontWeight: "800", fontSize: 12 }}>
                  {bloqueado ? (tipo === "idoso" ? "Idoso solicitado" : "PCD solicitado") : `Solicitar ${tipo === "idoso" ? "idoso" : "PCD"}`}
                </Text>
              </Pressable>
            );
          })}
        </View>
        <Text style={{ fontSize: 11, color: "#64748B", lineHeight: 17 }}>
          Envie/apresente a credencial por canal autorizado do estacionamento. Uma autodeclaração não é comprovação.
        </Text>
      </View>
      {erro ? <Text style={{ color: "#BE123C", fontSize: 12 }}>{erro}</Text> : null}
    </View>
  );
}
