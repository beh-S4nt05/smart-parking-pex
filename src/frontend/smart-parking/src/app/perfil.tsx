/**
 * Minha conta (RF-15) — motorista e papel de painel usam a mesma tela.
 * Backend: PUT /auth/me + PUT /auth/senha (troca derruba as outras sessões e
 * o app religa sozinho com a senha nova). Sem dependência nova: funciona no
 * Expo Go e no navegador exatamente igual.
 */
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Platform,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import { useRouter } from "expo-router";
import { useAuth } from "../hooks/useAuth";
import { apiErrorMessage, parkingApi } from "../services/api";
import { Botao, Card, Campo, Checkbox, Chip } from "../components/ui";
import Header from "../components/Header";
import Footer from "../components/Footer";
import { colors } from "../theme";

const ROLE_LABEL: Record<string, string> = {
  admin: "Admin global",
  gestor: "Gestor de estacionamento",
  financeiro: "Financeiro",
  usuario: "Motorista",
  publico: "Visita",
};

export default function Perfil() {
  const router = useRouter();
  const { user, loading, signIn, signOut, refreshUser } = useAuth();

  const [f, setF] = useState({ nome: "", telefone: "", placa: "", pcd: false });
  const [salvando, setSalvando] = useState(false);
  const [senha, setSenha] = useState({ atual: "", nova: "", confirma: "" });
  const [trocando, setTrocando] = useState(false);

  useEffect(() => {
    if (user) {
      setF({
        nome: user.nome ?? "",
        telefone: user.telefone ?? "",
        placa: user.placa_veiculo ?? "",
        pcd: Boolean(user.is_pcd),
      });
    }
  }, [user]);

  if (loading) {
    return (
      <View className="flex-1 items-center justify-center bg-white">
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (!user) {
    // sem sessão não há o que editar — manda para o login com retorno
    return (
      <View className="flex-1 items-center justify-center gap-4 bg-slate-50 px-6">
        <Text className="text-center text-base font-semibold text-slate-700">
          Entre na sua conta para editar o perfil.
        </Text>
        <Botao label="Ir para o login" onPress={() => router.push("/login")} />
      </View>
    );
  }

  const u = user; // narrowed após o guard — visível dentro das closures

  async function salvarCadastro() {
    if (f.nome.trim().length < 2) {
      Alert.alert("Confira os campos", "O nome precisa de pelo menos 2 caracteres.");
      return;
    }
    setSalvando(true);
    try {
      await parkingApi.atualizarMe({
        nome: f.nome.trim(),
        telefone: f.telefone.trim() || undefined,
        placa_veiculo: f.placa.trim() || undefined,
        is_pcd: f.pcd, // RF-47: declarar/revogar a elegibilidade PCD
      });
      await refreshUser();
      Alert.alert("Perfil atualizado ✅", "Já vale para a reserva da próxima vaga.");
    } catch (e) {
      Alert.alert("Não foi possível salvar", apiErrorMessage(e));
    } finally {
      setSalvando(false);
    }
  }

  async function trocarSenha() {
    if (senha.nova.length < 6) {
      Alert.alert("Senha curta", "A nova senha precisa de 6+ caracteres.");
      return;
    }
    if (senha.nova !== senha.confirma) {
      Alert.alert("Confirmação diferente", "Repita a nova senha igualzinho.");
      return;
    }
    setTrocando(true);
    try {
      await parkingApi.trocarSenha(senha.atual, senha.nova);
      // o backend revogou TODAS as sessões (padrão "mudei a senha, religue")
      // — religamos com a senha nova para o usuário não ser expulso no susto
      try {
        await signIn(u.email, senha.nova);
      } catch {
        await signOut();
      }
      setSenha({ atual: "", nova: "", confirma: "" });
      Alert.alert(
        "Senha alterada ✅",
        "As outras sessões suas foram encerradas; esta continua ativa.",
      );
    } catch (e) {
      Alert.alert("Não foi possível trocar", apiErrorMessage(e, "Senha atual incorreta?"));
    } finally {
      setTrocando(false);
    }
  }

  return (
    <View className="flex-1 bg-slate-50">
      <Header />
      <ScrollView className="flex-1" contentContainerStyle={{ paddingVertical: 20 }}>
        <View className="mx-auto w-full max-w-3xl gap-4 px-4">
          <View className="flex-row items-center justify-between">
            <View>
              <Text className="text-2xl font-extrabold text-slate-900">Minha conta</Text>
              <Text className="mt-0.5 text-[13px] text-slate-500">{user.email}</Text>
            </View>
            <Chip label={ROLE_LABEL[user.role] ?? user.role} tone="azul" />
          </View>

          <Card className="p-5">
            <Text className="mb-3 text-[15px] font-bold text-slate-800">Dados de cadastro</Text>
            <Campo label="Nome completo" value={f.nome} onChangeText={(v) => setF((p) => ({ ...p, nome: v }))} autoCapitalize="words" />
            <Campo label="Telefone" keyboardType="phone-pad" placeholder="(92) 99999-0000" value={f.telefone} onChangeText={(v) => setF((p) => ({ ...p, telefone: v }))} />
            <Campo label="Placa do veículo" autoCapitalize="characters" maxLength={8} placeholder="RRA1A23" value={f.placa} onChangeText={(v) => setF((p) => ({ ...p, placa: v }))} />
            <Checkbox
              checked={f.pcd}
              onPress={() => setF((p) => ({ ...p, pcd: !p.pcd }))}
              label="Sou pessoa com deficiência (PCD)"
              hint="Com a declaração, você ganha prioridade (e exclusividade) nas vagas PCD. Sem ela, o sistema sempre atribui vaga Comum."
            />
            <Text className="mt-1 text-xs text-slate-400">
              A placa entra na reserva para a leitura do portão — use maiúsculas sem hífen.
            </Text>
            <Botao
              label="Salvar alterações"
              onPress={salvarCadastro}
              loading={salvando}
              className="mt-4 self-start"
            />
          </Card>

          <Card className="p-5">
            <Text className="mb-1 text-[15px] font-bold text-slate-800">Segurança</Text>
            <Text className="mb-3 text-xs text-slate-500">
              Trocar a senha encerra todas as outras sessões (celular, navegador). RF-13/14.
            </Text>
            <Campo label="Senha atual" senha value={senha.atual} onChangeText={(v) => setSenha((p) => ({ ...p, atual: v }))} />
            <View className="flex-row gap-3">
              <View className="flex-1">
                <Campo label="Nova senha" senha value={senha.nova} onChangeText={(v) => setSenha((p) => ({ ...p, nova: v }))} />
              </View>
              <View className="flex-1">
                <Campo label="Confirmar" senha value={senha.confirma} onChangeText={(v) => setSenha((p) => ({ ...p, confirma: v }))} />
              </View>
            </View>
            <View className="mt-4 flex-row gap-2">
              <Botao label="Trocar senha" onPress={trocarSenha} loading={trocando} />
              <Botao
                label="Sair de todas as sessões"
                variant="contorno"
                className="border-red-300"
                onPress={async () => {
                  await signOut();
                  if (Platform.OS === "web") router.push("/login");
                  else router.replace("/login");
                }}
              />
            </View>
          </Card>

          <Text className="px-1 text-xs text-slate-400">
            Esqueceu a senha? Peça ao administrador do estacionamento uma senha temporária
            (balcão) — ele gera em Painel → Usuários → “Reset senha”.
          </Text>
        </View>
      </ScrollView>
      <Footer />
    </View>
  );
}
