// src/app/cadastro.tsx
import { useState } from "react";
import {
  View,
  Text,
  Pressable,
  TextInput,
  ActivityIndicator,
  ScrollView,
} from "react-native";
import { Link, useRouter } from "expo-router";

const PURPLE = "#6D28D9";

type FormState = {
  nome: string;
  email: string;
  telefone: string;
  senha: string;
  confirmarSenha: string;
  modeloCarro: string;
  placa: string;
};

type FormErrors = Partial<Record<keyof FormState, string>>;

function placaValida(valor: string) {
  const limpa = valor.toUpperCase().replace(/[^A-Z0-9]/g, "");
  const antigo = /^[A-Z]{3}[0-9]{4}$/;
  const mercosul = /^[A-Z]{3}[0-9][A-Z][0-9]{2}$/;
  return antigo.test(limpa) || mercosul.test(limpa);
}

function formatarTelefone(valor: string) {
  const numeros = valor.replace(/\D/g, "").slice(0, 11);
  if (numeros.length <= 2) return numeros;
  if (numeros.length <= 7) return `(${numeros.slice(0, 2)}) ${numeros.slice(2)}`;
  return `(${numeros.slice(0, 2)}) ${numeros.slice(2, 7)}-${numeros.slice(7)}`;
}

function formatarPlaca(valor: string) {
  return valor.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 7);
}

export default function Cadastro() {
  const router = useRouter();

  const [step, setStep] = useState<1 | 2>(1);
  const [form, setForm] = useState<FormState>({
    nome: "",
    email: "",
    telefone: "",
    senha: "",
    confirmarSenha: "",
    modeloCarro: "",
    placa: "",
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [loading, setLoading] = useState(false);

  function setField<K extends keyof FormState>(key: K, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => ({ ...prev, [key]: undefined }));
  }

  function validarEtapa1() {
    const novosErros: FormErrors = {};

    if (!form.nome.trim()) novosErros.nome = "Informe seu nome";

    if (!form.email.trim()) {
      novosErros.email = "Informe o e-mail";
    } else if (!/\S+@\S+\.\S+/.test(form.email)) {
      novosErros.email = "E-mail inválido";
    }

    const telefoneNumeros = form.telefone.replace(/\D/g, "");
    if (telefoneNumeros.length < 10) {
      novosErros.telefone = "Telefone inválido";
    }

    if (!form.senha) {
      novosErros.senha = "Informe a senha";
    } else if (form.senha.length < 8) {
      novosErros.senha = "Mínimo 8 caracteres";
    }

    if (form.confirmarSenha !== form.senha) {
      novosErros.confirmarSenha = "As senhas não coincidem";
    }

    setErrors(novosErros);
    return Object.keys(novosErros).length === 0;
  }

  // Só valida o veículo se o usuário preencheu algo — se os dois campos
  // estiverem vazios, consideramos que ele optou por pular essa etapa.
  function validarEtapa2ParaEnviar() {
    const algumPreenchido = form.modeloCarro.trim() || form.placa.trim();
    if (!algumPreenchido) return true;

    const novosErros: FormErrors = {};

    if (!form.modeloCarro.trim()) {
      novosErros.modeloCarro = "Informe o modelo do carro";
    }

    if (!form.placa.trim()) {
      novosErros.placa = "Informe a placa";
    } else if (!placaValida(form.placa)) {
      novosErros.placa = "Placa inválida (ex: ABC1234 ou ABC1D23)";
    }

    setErrors(novosErros);
    return Object.keys(novosErros).length === 0;
  }

  function handleAvancar() {
    if (!validarEtapa1()) return;
    setErrors({});
    setStep(2);
  }

  function handleVoltar() {
    setErrors({});
    setStep(1);
  }

  async function enviarCadastro(comCarro: boolean) {
    setLoading(true);
    try {
      const payload = comCarro
        ? form
        : { ...form, modeloCarro: "", placa: "" };

      // TODO: chamar sua API de cadastro aqui
      // await api.cadastrar(payload);

      router.replace("/login");
    } catch {
      setErrors({ placa: "Não foi possível criar a conta. Tente novamente." });
    } finally {
      setLoading(false);
    }
  }

  function handleCriarConta() {
    if (!validarEtapa2ParaEnviar()) return;
    const temCarro = Boolean(form.modeloCarro.trim() || form.placa.trim());
    enviarCadastro(temCarro);
  }

  function handlePular() {
    setErrors({});
    enviarCadastro(false);
  }

  return (
    <ScrollView
      className="flex-1 bg-slate-50"
      contentContainerStyle={{ flexGrow: 1, justifyContent: "center" }}
    >
      <View className="w-full max-w-md self-center px-6 py-10">
        {/* Cabeçalho */}
        <View className="mb-6 items-center">
          <View className="mb-3 h-12 w-12 items-center justify-center rounded-2xl bg-slate-900">
            <Text className="text-lg text-white">🚗</Text>
          </View>
          <Text className="text-xl font-bold text-slate-900">Criar conta</Text>
          <Text className="mt-1 text-center text-sm text-slate-500">
            {step === 1
              ? "Vamos começar com seus dados pessoais"
              : "Se quiser, cadastre seu veículo agora"}
          </Text>
        </View>

        {/* Indicador de progresso */}
        <View className="mb-5 flex-row items-center gap-2 px-1">
          <StepDot active number={1} done={step > 1} />
          <View className={`h-0.5 flex-1 ${step > 1 ? "bg-violet-700" : "bg-slate-200"}`} />
          <StepDot active={step === 2} number={2} done={false} />
        </View>
        <View className="mb-5 flex-row justify-between px-1">
          <Text className={`text-[11px] font-semibold ${step === 1 ? "text-violet-700" : "text-slate-400"}`}>
            Seus dados
          </Text>
          <Text className={`text-[11px] font-semibold ${step === 2 ? "text-violet-700" : "text-slate-400"}`}>
            Seu veículo (opcional)
          </Text>
        </View>

        {/* Card */}
        <View className="rounded-2xl bg-white p-6 shadow-sm">
          {step === 1 ? (
            <>
              <Field
                label="Nome completo"
                placeholder="Seu nome"
                autoCapitalize="words"
                value={form.nome}
                onChangeText={(v) => setField("nome", v)}
                error={errors.nome}
              />

              <Field
                label="E-mail"
                placeholder="voce@email.com"
                keyboardType="email-address"
                autoCapitalize="none"
                value={form.email}
                onChangeText={(v) => setField("email", v)}
                error={errors.email}
              />

              <Field
                label="Telefone"
                placeholder="(92) 9 9999-9999"
                keyboardType="phone-pad"
                value={form.telefone}
                onChangeText={(v) => setField("telefone", formatarTelefone(v))}
                error={errors.telefone}
              />

              <Field
                label="Senha"
                placeholder="Mínimo 8 caracteres"
                secureTextEntry
                autoCapitalize="none"
                value={form.senha}
                onChangeText={(v) => setField("senha", v)}
                error={errors.senha}
              />

              <Field
                label="Confirmar senha"
                placeholder="Repita a senha"
                secureTextEntry
                autoCapitalize="none"
                value={form.confirmarSenha}
                onChangeText={(v) => setField("confirmarSenha", v)}
                error={errors.confirmarSenha}
                last
              />

              <Pressable
                onPress={handleAvancar}
                className="mt-2 items-center rounded-xl py-3.5 active:opacity-90"
                style={{ backgroundColor: PURPLE }}
              >
                <Text className="text-base font-semibold text-white">Continuar</Text>
              </Pressable>

              <View className="mt-4 flex-row justify-center">
                <Text className="text-sm text-slate-500">Já tem conta? </Text>
                <Link href="/login" className="text-sm font-semibold text-violet-700">
                  Entrar
                </Link>
              </View>
            </>
          ) : (
            <>
              <Text className="mb-4 text-xs leading-relaxed text-slate-500">
                Você pode cadastrar seu veículo agora ou adicionar depois, direto
                no app — mas vai precisar dele na hora de reservar uma vaga.
              </Text>

              <Field
                label="Modelo do carro"
                placeholder="Ex: Honda Civic, Fiat Argo..."
                autoCapitalize="words"
                value={form.modeloCarro}
                onChangeText={(v) => setField("modeloCarro", v)}
                error={errors.modeloCarro}
              />

              <Field
                label="Placa"
                placeholder="ABC1234"
                autoCapitalize="characters"
                value={form.placa}
                onChangeText={(v) => setField("placa", formatarPlaca(v))}
                error={errors.placa}
                last
              />

              <Pressable
                onPress={handleCriarConta}
                disabled={loading}
                className="mt-2 items-center rounded-xl py-3.5 active:opacity-90 disabled:opacity-60"
                style={{ backgroundColor: PURPLE }}
              >
                {loading ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text className="text-base font-semibold text-white">Criar conta</Text>
                )}
              </Pressable>

              <Pressable
                onPress={handlePular}
                disabled={loading}
                className="mt-3 items-center rounded-xl border border-slate-200 py-3 active:bg-slate-50 disabled:opacity-60"
              >
                <Text className="text-sm font-semibold text-slate-600">
                  Pular por enquanto
                </Text>
              </Pressable>

              <Pressable onPress={handleVoltar} className="mt-4 items-center">
                <Text className="text-sm font-semibold text-slate-500">← Voltar</Text>
              </Pressable>
            </>
          )}
        </View>
      </View>
    </ScrollView>
  );
}

function StepDot({ number, active, done }: { number: number; active: boolean; done: boolean }) {
  return (
    <View
      className={`h-7 w-7 items-center justify-center rounded-full ${
        active || done ? "bg-violet-700" : "bg-slate-200"
      }`}
    >
      <Text className={`text-xs font-bold ${active || done ? "text-white" : "text-slate-500"}`}>
        {done ? "✓" : number}
      </Text>
    </View>
  );
}

function Field({
  label,
  error,
  last,
  ...inputProps
}: {
  label: string;
  error?: string;
  last?: boolean;
} & React.ComponentProps<typeof TextInput>) {
  return (
    <View className={last ? "mb-0" : "mb-3"}>
      <Text className="mb-1 text-xs font-semibold text-slate-700">{label}</Text>
      <TextInput
        placeholderTextColor="#94a3b8"
        className="rounded-xl bg-slate-100 px-4 py-2.5 text-sm text-slate-900"
        {...inputProps}
      />
      <Text className="mt-1 h-3.5 text-[11px] text-red-600">{error ?? ""}</Text>
    </View>
  );
}