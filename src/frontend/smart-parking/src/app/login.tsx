/**
 * Login — template "Login (MOBILE/WEB)" do Figma:
 * - mobile: tela branca com logo P azul + formulário central
 * - web: split com painel de marca azul à esquerda
 * Integração real: POST /auth/login aceita e-mail OU telefone e devolve o
 * usuário no mesmo response; AuthContext guarda os tokens. Redirecionamento
 * por papel: staff → painel, motorista → Home/Mapa.
 */
import { useState } from "react";
import {
  KeyboardAvoidingView,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  Text,
  View,
  useWindowDimensions,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useAuth } from "../hooks/useAuth";
import { apiErrorMessage } from "../services/api";
import { destinoAposLogin } from "../services/authFlow";
import { Botao, Campo, Logo } from "../components/ui";

export default function Login() {
  const router = useRouter();
  const { next } = useLocalSearchParams<{ next?: string | string[] }>();
  const { width } = useWindowDimensions();
  const isWide = width >= 900;
  const { signIn } = useAuth();

  // "← Início" com destino garantido: router.back() sozinho é mudo quando se
  // chega ao /login direto (URL digitada, redirecionamento 403 do painel)
  const voltarInicio = () => {
    if (router.canGoBack()) router.back();
    else router.replace("/");
  };

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [senhaVisivel, setSenhaVisivel] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [recuperar, setRecuperar] = useState(false);

  const [erros, setErros] = useState<{ email?: string; senha?: string }>({});
  const [loading, setLoading] = useState(false);

  async function handleEntrar() {
    const novos: typeof erros = {};
    if (!email.trim()) novos.email = "Informe seu e-mail ou telefone";
    if (!senha) novos.senha = "Informe sua senha";
    setErros(novos);
    if (Object.keys(novos).length > 0) return;

    setLoading(true);
    setErro(null);
    try {
      const usuario = await signIn(email, senha);
      // Retorna ao mapa/QR que pediu autenticação, sem aceitar URL externa
      // nem liberar painel/simulador para um papel sem permissão.
      router.replace(destinoAposLogin(next, usuario.role) as never);
    } catch (e) {
      setErro(apiErrorMessage(e, "Não foi possível entrar."));
    } finally {
      setLoading(false);
    }
  }

  const formulario = (
    <View className="w-full max-w-[420px] px-6 py-8">
      {!isWide && (
        <View className="mb-7 items-center">
          <Logo size={56} />
          <Text className="mt-4 text-[22px] font-extrabold text-slate-900">
            Bem-vindo ao Smart Parking
          </Text>
          <Text className="mt-1 text-sm text-slate-500">
            Entre para acessar sua conta
          </Text>
        </View>
      )}

      <Campo
        label="E-mail ou telefone"
        placeholder="voce@email.com"
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="email-address"
        value={email}
        onChangeText={(v) => {
          setEmail(v);
          setErros((p) => ({ ...p, email: undefined }));
        }}
        erro={erros.email}
      />

      <Campo
        label="Senha"
        placeholder="••••••••"
        senha
        visivel={senhaVisivel}
        onAlternarVisivel={() => setSenhaVisivel((v) => !v)}
        value={senha}
        onChangeText={(v) => {
          setSenha(v);
          setErros((p) => ({ ...p, senha: undefined }));
        }}
        onSubmitEditing={handleEntrar}
        returnKeyType="go"
        erro={erros.senha}
      />

      <View className="-mt-1 mb-4 flex-row justify-end">
        <Pressable onPress={() => setRecuperar((v) => !v)}>
          <Text className="text-xs font-semibold text-blue-700">
            Esqueci minha senha
          </Text>
        </Pressable>
      </View>

      {recuperar ? (
        <View className="mb-4 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3">
          <Text className="text-[13px] font-semibold text-slate-800">
            Como recuperar o acesso
          </Text>
          <Text className="mt-1 text-xs leading-4 text-slate-600">
            O app não tem e-mail transacional: peça ao administrador do
            estacionamento uma senha temporária (Painel → Usuários → “Reset
            senha”). Ela derruba suas sessões antigas — entre com ela e troque
            em “Minha conta”.
          </Text>
          <Pressable
            onPress={() =>
              Linking.openURL(
                "mailto:behsolutionsandautomations@gmail.com?subject=Recuperar%20acesso%20Smart%20Parking",
              )
            }
            className="mt-2 self-start rounded-full bg-white px-3 py-1.5"
          >
            <Text className="text-xs font-bold text-blue-700">
              Ou fale com o suporte por e-mail
            </Text>
          </Pressable>
        </View>
      ) : null}

      {erro ? (
        <View className="mb-4 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5">
          <Text className="text-[13px] font-medium text-red-600">{erro}</Text>
        </View>
      ) : null}

      <Botao
        label="Entrar"
        onPress={handleEntrar}
        loading={loading}
        className="w-full"
      />

      <Text className="mt-6 text-center text-sm text-slate-500">
        Não tem conta?{" "}
        <Text className="font-bold text-blue-700" onPress={() => router.push("/cadastro")}>
          Cadastre-se
        </Text>
      </Text>

      {/* Atalhos de demonstração (credenciais do seed) — ACH-02: aparecem só
          em build de desenvolvimento; num app de produção eles somem sozinhos. */}
      {__DEV__ ? (
      <View className="mt-8 rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <Text className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
          Acesso rápido (demo)
        </Text>
        <View className="mt-2.5 gap-2">
          <Pressable
            onPress={() => {
              setEmail("motorista@smartparking.com");
              setSenha("motor123");
              setErro(null);
            }}
            className="flex-row items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2 active:bg-blue-50"
          >
            <Text className="text-[13px] font-semibold text-slate-700">
              🚗 Motorista
            </Text>
            <Text className="text-[11px] text-slate-400">
              motorista@smartparking.com
            </Text>
          </Pressable>
          <Pressable
            onPress={() => {
              setEmail("admin@smartparking.com");
              setSenha("admin123");
              setErro(null);
            }}
            className="flex-row items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2 active:bg-blue-50"
          >
            <Text className="text-[13px] font-semibold text-slate-700">
              🛠️ Administrador
            </Text>
            <Text className="text-[11px] text-slate-400">
              admin@smartparking.com
            </Text>
          </Pressable>
        </View>
      </View>
      ) : null}
    </View>
  );

  if (isWide) {
    return (
      <View className="flex-1 flex-row bg-white">
        <View className="w-[45%] items-center justify-center bg-blue-600 px-12">
          <View className="w-full max-w-sm gap-5">
            <Logo size={52} tone="white" />
            <Text className="text-4xl font-extrabold text-white">Smart Parking</Text>
            <Text className="text-base leading-6 text-blue-100">
              Monitoramento inteligente de vagas em shoppings de Manaus, em tempo
              real.
            </Text>
          </View>
        </View>
        <ScrollView
          className="flex-1"
          contentContainerStyle={{
            flexGrow: 1,
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <View className="w-full max-w-[420px] px-8 py-10">
            <Pressable
              onPress={voltarInicio}
              accessibilityRole="button"
              className="mb-5 flex-row items-center gap-1.5 self-start rounded-full border border-slate-200 bg-white px-3.5 py-1.5 active:bg-slate-50"
            >
              <Text className="text-[15px] leading-5 text-blue-600">←</Text>
              <Text className="text-[13px] font-semibold text-slate-600">Início</Text>
            </Pressable>
            <Text className="text-3xl font-extrabold text-slate-900">Entrar</Text>
            <Text className="mb-5 mt-1.5 text-sm text-slate-500">
              Acesse sua conta para continuar
            </Text>
            {formulario}
          </View>
        </ScrollView>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      className="flex-1 bg-white"
    >
      <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: "center" }}>
        {/* antes: absolute top-4 — com edge-to-edge no Android o toque caía na
            barra de status do sistema, nunca no botão. Agora vive no fluxo e
            herda o respiro seguro do _layout (queda clicável garantida). */}
        <Pressable
          onPress={voltarInicio}
          accessibilityRole="button"
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          className="ml-6 mt-4 flex-row items-center gap-1.5 self-start rounded-full border border-slate-200 bg-white px-3 py-1.5 active:bg-slate-50"
        >
          <Text className="text-[15px] leading-5 text-blue-600">←</Text>
          <Text className="text-[13px] font-semibold text-slate-600">Início</Text>
        </Pressable>
        <View className="items-center">{formulario}</View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
