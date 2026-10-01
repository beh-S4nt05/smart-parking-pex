// src/app/login.tsx
import { useState } from "react";
import {
  View,
  Text,
  Pressable,
  TextInput,
  ActivityIndicator,
  ScrollView,
  useWindowDimensions,
} from "react-native";
import { Link, useRouter } from "expo-router";

const PURPLE = "#6D28D9";

export default function Login() {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const isWide = width >= 900;

  const [mode, setMode] = useState<"entrar" | "criar">("entrar");
  const [channel, setChannel] = useState<"email" | "telefone">("email");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; senha?: string }>({});

  function validar() {
    const novosErros: typeof errors = {};
    if (!email.trim()) novosErros.email = "Informe o e-mail";
    if (!senha) novosErros.senha = "Informe a senha";
    setErrors(novosErros);
    return Object.keys(novosErros).length === 0;
  }

  async function handleLogin() {
    if (!validar()) return;
    setLoading(true);
    try {
      router.replace("/");
    } catch {
      setErrors({ senha: "E-mail ou senha incorretos" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScrollView
      className="flex-1 bg-slate-50"
      contentContainerStyle={{ flexGrow: 1 }}
    >
      {/* Topo */}
      <View className="flex-row items-center justify-between px-6 py-5 md:px-12">
        <View className="flex-row items-center gap-2">
          <View className="h-9 w-9 items-center justify-center rounded-lg bg-slate-900">
            <Text className="text-white">🚗</Text>
          </View>
          <View>
            <Text className="text-sm font-bold text-slate-900">Smart Parking</Text>
            <Text className="text-xs text-slate-400">Shoppings</Text>
          </View>
        </View>

        <Link href="/" className="text-sm font-medium text-violet-700">
          ← Voltar ao início
        </Link>
      </View>

        <View className="w-full max-w-md self-center rounded-2xl bg-white p-6 shadow-sm md:self-center">
          <View className="mb-6 flex-row rounded-full bg-slate-100 p-1">
            <TabButton
              label="Entrar"
              active={mode === "entrar"}
              onPress={() => setMode("entrar")}
            />
            <TabButton
              label="Criar conta"
              active={mode === "criar"}
              onPress={() => router.push("/cadastro")}
            />
          </View>

          <Text className="mb-1 text-xl font-bold text-slate-900">
            Bem-vindo de volta
          </Text>
          <Text className="mb-5 text-sm text-slate-500">
            Acesse sua conta para reservar e ver seu histórico.
          </Text>

          <View className="mb-5 flex-row gap-3">
            <SocialButton label="Google" icon="G" />
            <SocialButton label="Apple" icon="" />
          </View>

          <View className="mb-5 flex-row items-center gap-3">
            <View className="h-px flex-1 bg-slate-200" />
            <Text className="text-xs text-slate-400">ou continue com</Text>
            <View className="h-px flex-1 bg-slate-200" />
          </View>

          <View className="mb-4 flex-row gap-5">
            <ChannelTab
              label="E-mail"
              active={channel === "email"}
              onPress={() => setChannel("email")}
            />
            <ChannelTab
              label="Telefone"
              active={channel === "telefone"}
              onPress={() => setChannel("telefone")}
            />
          </View>

          <Text className="mb-1.5 text-sm font-semibold text-slate-700">
            {channel === "email" ? "E-mail" : "Telefone"}
          </Text>
          <TextInput
            placeholder={channel === "email" ? "voce@email.com" : "(92) 9 9999-9999"}
            placeholderTextColor="#94a3b8"
            keyboardType={channel === "email" ? "email-address" : "phone-pad"}
            autoCapitalize="none"
            value={email}
            onChangeText={setEmail}
            className="rounded-xl bg-slate-100 px-4 py-3 text-base text-slate-900"
          />
          <Text className="mb-4 mt-1 h-4 text-xs text-red-600">
            {errors.email ?? ""}
          </Text>

          <Text className="mb-1.5 text-sm font-semibold text-slate-700">Senha</Text>
          <TextInput
            placeholder="Mínimo 8 caracteres"
            placeholderTextColor="#94a3b8"
            secureTextEntry
            value={senha}
            onChangeText={setSenha}
            className="rounded-xl bg-slate-100 px-4 py-3 text-base text-slate-900"
          />
          <Text className="mb-2 mt-1 h-4 text-xs text-red-600">
            {errors.senha ?? ""}
          </Text>

          <View className="mb-5 flex-row items-center justify-between">
            <Pressable>
              <Text className="text-xs text-slate-500">Prefere sem senha?</Text>
            </Pressable>
            <Pressable>
              <Text className="text-xs font-semibold text-violet-700">
                Receber código
              </Text>
            </Pressable>
          </View>

          <Pressable
            onPress={handleLogin}
            disabled={loading}
            className="items-center rounded-xl py-3.5 active:opacity-90 disabled:opacity-60"
            style={{ backgroundColor: PURPLE }}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text className="text-base font-semibold text-white">Entrar</Text>
            )}
          </Pressable>

          <Pressable className="mt-4 items-center">
            <Text className="text-sm font-medium text-violet-700">
              Esqueci minha senha
            </Text>
          </Pressable>
        </View>

      {/* Rodapé — agora dentro do fluxo de scroll, não mais espremido */}
      <Text className="px-6 pb-6 pt-4 text-center text-xs text-slate-400">
        © 2026 Smart Parking Shoppings · (92) 98123-0258 ·
        behsolutionsandautomations@gmail.com · Manaus, AM
      </Text>
    </ScrollView>
  );
}

function StatCard({ value, label }: { value: string; label: string }) {
  return (
    <View className="flex-1 items-center rounded-xl bg-white/15 py-3">
      <Text className="text-lg font-bold text-white">{value}</Text>
      <Text className="text-xs text-violet-100">{label}</Text>
    </View>
  );
}

function TabButton({ label, active, onPress }: { label: string; active: boolean; onPress: () => void }) {
  return (
    <Pressable
      onPress={onPress}
      className={`flex-1 items-center rounded-full py-2 ${active ? "bg-violet-700" : ""}`}
    >
      <Text className={`text-sm font-semibold ${active ? "text-white" : "text-slate-500"}`}>
        {label}
      </Text>
    </Pressable>
  );
}

function ChannelTab({ label, active, onPress }: { label: string; active: boolean; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} className="pb-1">
      <Text
        className={`text-sm font-semibold ${
          active ? "border-b-2 border-violet-700 text-violet-700" : "text-slate-400"
        }`}
      >
        {label}
      </Text>
    </Pressable>
  );
}

function SocialButton({ label, icon }: { label: string; icon: string }) {
  return (
    <Pressable className="flex-1 flex-row items-center justify-center gap-2 rounded-xl border border-slate-200 py-3 active:bg-slate-50">
      <Text className="text-base">{icon}</Text>
      <Text className="text-sm font-medium text-slate-700">{label}</Text>
    </Pressable>
  );
}