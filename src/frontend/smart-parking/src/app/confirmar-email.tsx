/** Confirmação real da caixa postal após o cadastro.
 * Nunca confunda e-mail com prova de identidade ou credencial PCD/idoso.
 * O código só é validado pelo backend, com uso único e limite de tentativas.
 */
import { useState } from "react";
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Botao, Campo, Logo } from "../components/ui";
import { apiErrorMessage, parkingApi } from "../services/api";

export default function ConfirmarEmail() {
  const router = useRouter();
  const params = useLocalSearchParams<{ email?: string | string[] }>();
  const predefinido = typeof params.email === "string" ? params.email : "";
  const [email, setEmail] = useState(predefinido);
  const [codigo, setCodigo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [verificando, setVerificando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const valido = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
  const codigoValido = /^[0-9]{6}$/.test(codigo);
  async function confirmar() {
    if (!valido || !codigoValido || verificando) {
      setErro("Informe seu e-mail e o código de 6 dígitos enviado a ele.");
      return;
    }
    setVerificando(true);
    setErro(null);
    try {
      await parkingApi.confirmarEmail(email, codigo);
      router.replace("/login" as never);
    } catch (e) {
      setErro(apiErrorMessage(e, "Não foi possível confirmar o código. Verifique e tente novamente."));
    } finally {
      setVerificando(false);
    }
  }

  async function reenviar() {
    if (!valido || enviando) {
      setErro("Informe um endereço de e-mail válido para solicitar o código.");
      return;
    }
    setEnviando(true);
    setErro(null);
    setInfo(null);
    try {
      await parkingApi.solicitarConfirmacaoEmail(email);
      setInfo("Se a conta estiver pendente, enviaremos um novo código. Aguarde pelo menos 60 segundos antes de solicitar outro e verifique o spam.");
    } catch (e) {
      setErro(apiErrorMessage(e, "Não foi possível solicitar outro código agora."));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1, backgroundColor: "#F3F7FD" }}>
      <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ flexGrow: 1, justifyContent: "center", padding: 20 }}>
        <View style={{ width: "100%", maxWidth: 480, alignSelf: "center", backgroundColor: "#FFFFFF", padding: 24, borderRadius: 22, borderWidth: 1, borderColor: "#E2E8F0" }}>
          <View style={{ alignItems: "center", marginBottom: 18 }}>
            <Logo size={55} />
            <Ionicons name="mail-unread-outline" size={32} color="#2563EB" style={{ marginTop: 14 }} />
            <Text style={{ color: "#0F1E38", fontWeight: "800", fontSize: 24, textAlign: "center", marginTop: 8 }}>
              Confirme seu e-mail
            </Text>
            <Text style={{ color: "#475569", textAlign: "center", fontSize: 14, lineHeight: 21, marginTop: 8 }}>
              Enviamos um código de 6 dígitos pelo e-mail da empresa. Ele vale por 10 minutos e só pode ser utilizado uma vez.
            </Text>
          </View>
          <Campo label="E-mail cadastrado" keyboardType="email-address" autoCapitalize="none" autoCorrect={false} value={email} onChangeText={setEmail} />
          <Campo label="Código recebido" keyboardType="number-pad" autoComplete="one-time-code" textContentType="oneTimeCode" maxLength={6} value={codigo} onChangeText={v => setCodigo(v.replace(/\D/g, "").slice(0, 6))} />
          {erro ? (
            <Text accessibilityRole="alert" style={{ color: "#B91C1C", marginBottom: 12, fontSize: 13 }}>{erro}</Text>
          ) : null}
          {info ? (
            <Text accessibilityLiveRegion="polite" style={{ color: "#166534", marginBottom: 12, fontSize: 13 }}>{info}</Text>
          ) : null}
          <Botao label="Confirmar código" loading={verificando} disabled={!codigoValido || !valido || enviando} onPress={confirmar} />
          <Pressable onPress={reenviar} disabled={enviando || verificando} accessibilityRole="button" accessibilityLabel="Reenviar código de confirmação" style={{ padding: 14, alignItems: "center", marginTop: 8 }}>
            <Text style={{ color: "#2563EB", fontWeight: "700", fontSize: 14 }}>{enviando ? "Solicitando..." : "Não recebi o código — reenviar"}</Text>
          </Pressable>
          <Pressable onPress={() => router.replace("/login" as never)} accessibilityRole="link" style={{ padding: 12, alignItems: "center" }}>
            <Text style={{ color: "#475569", fontSize: 13 }}>Voltar ao login</Text>
          </Pressable>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
