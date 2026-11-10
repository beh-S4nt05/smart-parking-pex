/**
 * Login — template "Login (MOBILE/WEB)" do Figma:
 * - mobile: tela branca com logo P azul + formulário central
 * - web: split com painel de marca azul à esquerda (a partir de 1024px)
 * Integração real: POST /auth/login aceita e-mail OU telefone e devolve o
 * usuário no mesmo response; AuthContext guarda os tokens. Redirecionamento
 * por papel: staff / painel, motorista / Home/Mapa.
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
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useAuth } from "../hooks/useAuth";
import { apiErrorMessage } from "../services/api";
import { destinoAposLogin } from "../services/authFlow";
import { Botao, Campo, IconeVoltar, Logo } from "../components/ui";

export default function Login() {
  const router = useRouter();
  const { next } = useLocalSearchParams<{ next?: string | string[] }>();
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
    <View className="w-full">
      <Campo
        label="E-mail ou telefone"
        placeholder="voce@email.com"
        autoCapitalize="none"
        autoCorrect={false}
        autoComplete="username"
        textContentType="username"
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
        autoComplete="current-password"
        textContentType="password"
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
        <Pressable
          onPress={() => setRecuperar((v) => !v)}
          accessibilityRole="button"
          accessibilityLabel="Esqueci minha senha"
          accessibilityHint="Mostra orientações para recuperar o acesso"
          accessibilityState={{ expanded: recuperar }}
          aria-expanded={recuperar}
          hitSlop={8}
          className="min-h-11 flex-row items-center justify-center rounded-md px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <Text className="text-xs font-semibold text-blue-700">
            Esqueci minha senha
          </Text>
        </Pressable>
      </View>

      {recuperar ? (
        <View
          nativeID="recuperar-acesso"
          accessibilityLabel="Como recuperar o acesso"
          className="mb-4 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3"
        >
          <Text className="text-[13px] font-semibold text-slate-800">
            Como recuperar o acesso
          </Text>
          <Text className="mt-1 text-xs leading-4 text-slate-600">
            O app não tem e-mail transacional: peça ao administrador do
            estacionamento uma senha temporária (Painel / Usuários / “Reset
            senha”). Ela derruba suas sessões antigas — entre com ela e troque
            em “Minha conta”.
          </Text>
          <Pressable
            onPress={() =>
              Linking.openURL(
                "mailto:behsolutionsandautomations@gmail.com?subject=Recuperar%20acesso%20Smart%20Parking",
              )
            }
            accessibilityRole="button"
            accessibilityLabel="Falar com o suporte por e-mail"
            hitSlop={4}
            className="mt-2 min-h-11 flex-row items-center self-start rounded-full bg-white px-3 py-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <Text className="text-xs font-bold text-blue-700">
              Ou fale com o suporte por e-mail
            </Text>
          </Pressable>
        </View>
      ) : null}

      {erro ? (
        <View
          nativeID="login-erro"
          accessibilityRole="alert"
          accessibilityLiveRegion="polite"
          className="mb-4 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5"
        >
          <Text className="text-[13px] font-medium text-red-600">{erro}</Text>
        </View>
      ) : null}

      <Botao
        label="Entrar"
        onPress={handleEntrar}
        loading={loading}
        className="w-full"
      />

      <View className="mt-6 flex-row flex-wrap items-center justify-center gap-1">
        <Text className="text-sm text-slate-600">Não tem conta?</Text>
        <Pressable
          onPress={() => router.push("/cadastro")}
          accessibilityRole="button"
          accessibilityLabel="Cadastre-se"
          hitSlop={8}
          className="min-h-11 flex-row items-center justify-center rounded-md px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <Text className="text-sm font-bold text-blue-700">Cadastre-se</Text>
        </Pressable>
      </View>

      {/* Atalhos de demonstração (credenciais do seed) — ACH-02: aparecem só
          em build de desenvolvimento; num app de produção eles somem sozinhos. */}
      {__DEV__ ? (
      <View className="mt-8 rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <Text className="text-[11px] font-bold uppercase tracking-wider text-slate-600">
          Acesso rápido (demo)
        </Text>
        <View className="mt-2.5 gap-2">
          <Pressable
            onPress={() => {
              setEmail("motorista@smartparking.com");
              setSenha("motor123");
              setErro(null);
            }}
            accessibilityRole="button"
            accessibilityLabel="Preencher credenciais do motorista"
            hitSlop={4}
            className="flex-row items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2 active:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <Text className="text-[13px] font-semibold text-slate-700">
              Motorista
            </Text>
            <Text className="text-[11px] text-slate-600">
              motorista@smartparking.com
            </Text>
          </Pressable>
          <Pressable
            onPress={() => {
              setEmail("admin@smartparking.com");
              setSenha("admin123");
              setErro(null);
            }}
            accessibilityRole="button"
            accessibilityLabel="Preencher credenciais do administrador"
            hitSlop={4}
            className="flex-row items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2 active:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <Text className="text-[13px] font-semibold text-slate-700">
              Administrador
            </Text>
            <Text className="text-[11px] text-slate-600">
              admin@smartparking.com
            </Text>
          </Pressable>
        </View>
      </View>
      ) : null}
    </View>
  );

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      className="flex-1 bg-white"
    >
      <View className="flex-1 flex-row bg-white">
        {/* Painel de marca apenas em desktop real (>= 1024px). CSS puro: o
            pré-render já nasce com o split, sem o "flash" do layout mobile
            que aparecia enquanto useLarguraResponsiva hidratava. */}
        <View className="hidden w-[45%] min-w-0 items-center justify-center bg-blue-600 px-12 lg:flex">
          <View className="w-full max-w-sm gap-5">
            <Logo size={52} tone="white" />
            <Text accessibilityRole="header" className="text-4xl font-extrabold text-white">
              Smart Parking
            </Text>
            <Text className="text-base leading-6 text-blue-50">
              Monitoramento inteligente de vagas em shoppings de Manaus, em tempo
              real.
            </Text>
          </View>
        </View>

        <ScrollView
          className="min-w-0 flex-1"
          contentContainerStyle={{
            flexGrow: 1,
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <View className="w-full max-w-[420px] px-6 py-8 sm:px-8">
            {/* botão de voltar vive no fluxo: edge-to-edge no Android não
                deixa o toque cair na barra de status do sistema. */}
            <Pressable
              onPress={voltarInicio}
              accessibilityRole="button"
              accessibilityLabel="Voltar ao Início"
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
              className="mb-5 min-h-11 flex-row items-center gap-2 self-start rounded-full border border-slate-200 bg-white px-3.5 py-1.5 active:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              <IconeVoltar />
              <Text className="text-[13px] font-semibold text-slate-600">Início</Text>
            </Pressable>

            <View className="mb-5 hidden lg:flex">
              <Text accessibilityRole="header" className="text-3xl font-extrabold text-slate-900">
                Entrar
              </Text>
              <Text className="mt-1.5 text-sm text-slate-600">
                Acesse sua conta para continuar
              </Text>
            </View>

            <View className="mb-7 items-center lg:hidden">
              <Logo size={56} />
              <Text accessibilityRole="header" className="mt-4 text-[22px] font-extrabold text-slate-900">
                Bem-vindo ao Smart Parking
              </Text>
              <Text className="mt-1 text-sm text-slate-600">
                Entre para acessar sua conta
              </Text>
            </View>

            {formulario}
          </View>
        </ScrollView>
      </View>
    </KeyboardAvoidingView>
  );
}
