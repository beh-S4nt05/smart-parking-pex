import { Link, useRouter } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, Pressable, Text, View } from "react-native";
import FormField from "@/components/FormField";

export default function Login() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [errors, setErrors] = useState<{ email?: string; senha?: string }>({});
  const [loading, setLoading] = useState(false);

  function validar() {
    const novosErros: { email?: string; senha?: string } = {};

    if (!email.trim()) {
      novosErros.email = "Informe o e-mail";
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      novosErros.email = "E-mail inválido";
    }

    if (!senha) {
      novosErros.senha = "Informe a senha";
    } else if (senha.length < 6) {
      novosErros.senha = "A senha deve ter pelo menos 6 caracteres";
    }

    setErrors(novosErros);
    return Object.keys(novosErros).length === 0;
  }

  async function handleLogin() {
    if (!validar()) return;

    setLoading(true);
    try {
      // TODO: chamar sua API/autenticação aqui
      // await api.login(email, senha);
      router.replace("/cadastro");
    } catch (err) {
      setErrors({ senha: "E-mail ou senha incorretos" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <View className="flex-1 justify-center bg-slate-50 px-6">
      <Text className="mb-1 text-2xl font-bold text-slate-900">Entrar</Text>
      <Text className="mb-6 text-sm text-slate-500">
        Acesse sua conta para continuar
      </Text>

      <FormField
        label="E-mail"
        placeholder="seu@email.com"
        keyboardType="email-address"
        autoCapitalize="none"
        autoComplete="email"
        value={email}
        onChangeText={setEmail}
        error={errors.email}
      />

      <FormField
        label="Senha"
        placeholder="••••••••"
        password
        autoCapitalize="none"
        autoComplete="password"
        value={senha}
        onChangeText={setSenha}
        error={errors.senha}
      />

      <Pressable
        onPress={handleLogin}
        disabled={loading}
        className="mt-2 items-center rounded-xl bg-blue-600 py-3 active:bg-blue-700 disabled:opacity-60"
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text className="text-base font-semibold text-white">Entrar</Text>
        )}
      </Pressable>

      <View className="mt-4 flex-row justify-center">
        <Text className="text-sm text-slate-500">Não tem conta? </Text>
        <Link href="/cadastro" className="text-sm font-semibold text-blue-600">
          Cadastre-se
        </Link>
      </View>
    </View>
  );
}