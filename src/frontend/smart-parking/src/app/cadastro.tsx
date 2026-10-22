/**
 * Cadastro em 2 etapas (dados pessoais + veículo opcional), agora integrado:
 * POST /auth/registrar → auto-login via /auth/login → redireciona por papel.
 * Mantém o fluxo existente, com a paleta azul dos templates do Figma.
 */
import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import { useRouter } from "expo-router";
import { useAuth } from "../hooks/useAuth";
import { apiErrorMessage } from "../services/api";
import { Botao, Campo, Checkbox, Logo } from "../components/ui";

type FormState = {
  nome: string;
  email: string;
  telefone: string;
  senha: string;
  confirmarSenha: string;
  modeloCarro: string;
  placa: string;
  /** RF-47: autodeclaração PCD — habilita prioridade/exclusividade nas PCD. */
  pcd: boolean;
};

type FormErrors = Partial<Record<keyof FormState, string>>;

function placaValida(valor: string) {
  const limpa = valor.toUpperCase().replace(/[^A-Z0-9]/g, "");
  return (
    /^[A-Z]{3}[0-9]{4}$/.test(limpa) || /^[A-Z]{3}[0-9][A-Z][0-9]{2}$/.test(limpa)
  );
}

function formatarTelefone(valor: string) {
  const n = valor.replace(/\D/g, "").slice(0, 11);
  if (n.length <= 2) return n;
  if (n.length <= 7) return `(${n.slice(0, 2)}) ${n.slice(2)}`;
  return `(${n.slice(0, 2)}) ${n.slice(2, 7)}-${n.slice(7)}`;
}

function formatarPlaca(valor: string) {
  return valor.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 7);
}

export default function Cadastro() {
  const router = useRouter();
  const { signIn, register } = useAuth();

  const [step, setStep] = useState<1 | 2>(1);
  const [form, setForm] = useState<FormState>({
    nome: "",
    email: "",
    telefone: "",
    senha: "",
    confirmarSenha: "",
    modeloCarro: "",
    placa: "",
    pcd: false,
});
  const [errors, setErrors] = useState<FormErrors>({});
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [senhaVisivel, setSenhaVisivel] = useState(false);

  function setField<K extends keyof FormState>(key: K, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => ({ ...prev, [key]: undefined }));
  }

  function validarEtapa1() {
    const e: FormErrors = {};
    if (!form.nome.trim()) e.nome = "Informe seu nome";
    if (!form.email.trim()) e.email = "Informe o e-mail";
    else if (!/\S+@\S+\.\S+/.test(form.email)) e.email = "E-mail inválido";

    const tel = form.telefone.replace(/\D/g, "");
    if (!tel) e.telefone = "Informe seu telefone";
    else if (tel.length < 10) e.telefone = "Telefone inválido";

    if (!form.senha) e.senha = "Informe a senha";
    else if (form.senha.length < 8) e.senha = "Mínimo 8 caracteres";

    if (form.confirmarSenha !== form.senha)
      e.confirmarSenha = "As senhas não coincidem";

    setErrors(e);
    return Object.keys(e).length === 0;
  }

  function validarEtapa2() {
    const preenchido = form.modeloCarro.trim() || form.placa.trim();
    if (!preenchido) return true; // pulou o veículo
    const e: FormErrors = {};
    if (!form.modeloCarro.trim()) e.modeloCarro = "Informe o modelo do carro";
    if (!form.placa.trim()) e.placa = "Informe a placa";
    else if (!placaValida(form.placa))
      e.placa = "Placa inválida (ex: ABC1D23)";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function enviar() {
    setLoading(true);
    setErroGeral(null);
    try {
      await register({
        nome: form.nome.trim(),
        email: form.email.trim().toLowerCase(),
        senha: form.senha,
        telefone: form.telefone.replace(/\D/g, ""),
        placa_veiculo: form.placa ? formatarPlaca(form.placa) : undefined,
        is_pcd: form.pcd,
      });
      // login automático após criar a conta
      await signIn(form.email, form.senha);
      router.replace("/");
    } catch (err) {
      setErroGeral(apiErrorMessage(err, "Não foi possível criar a conta."));
      if (step === 2 && /placa|email|e-mail/i.test(String(erroGeral))) setStep(1);
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      className="flex-1 bg-slate-50"
    >
      <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: "center" }}>
        <View className="w-full max-w-[440px] self-center px-5 py-10">
          <View className="mb-6 items-center">
            <Logo size={48} />
            <Text className="mt-3 text-2xl font-extrabold text-slate-900">
              Criar conta
            </Text>
            <Text className="mt-1 text-center text-sm text-slate-500">
              {step === 1
                ? "Vamos começar com seus dados pessoais"
                : "Se quiser, cadastre seu veículo agora"}
            </Text>
          </View>

          {/* progresso */}
          <View className="mb-2 flex-row items-center gap-2 px-1">
            <PassoEtapa numero={1} ativo={step === 1} concluido={step > 1} />
            <View
              className={`h-0.5 flex-1 ${step > 1 ? "bg-blue-600" : "bg-slate-200"}`}
            />
            <PassoEtapa numero={2} ativo={step === 2} concluido={false} />
          </View>
          <View className="mb-5 flex-row justify-between px-1">
            <Text
              className={`text-[11px] font-semibold ${step === 1 ? "text-blue-700" : "text-slate-400"}`}
            >
              Seus dados
            </Text>
            <Text
              className={`text-[11px] font-semibold ${step === 2 ? "text-blue-700" : "text-slate-400"}`}
            >
              Seu veículo (opcional)
            </Text>
          </View>

          <View className="rounded-2xl border border-slate-200 bg-white p-6">
            {step === 1 ? (
              <>
                <Campo
                  label="Nome completo"
                  placeholder="Seu nome"
                  autoCapitalize="words"
                  value={form.nome}
                  onChangeText={(v) => setField("nome", v)}
                  erro={errors.nome}
                />
                <Campo
                  label="E-mail"
                  placeholder="voce@email.com"
                  keyboardType="email-address"
                  autoCapitalize="none"
                  autoCorrect={false}
                  value={form.email}
                  onChangeText={(v) => setField("email", v)}
                  erro={errors.email}
                />
                <Campo
                  label="Telefone"
                  placeholder="(92) 9 9999-9999"
                  keyboardType="phone-pad"
                  value={form.telefone}
                  onChangeText={(v) => setField("telefone", formatarTelefone(v))}
                  erro={errors.telefone}
                />
                <Campo
                  label="Senha"
                  placeholder="Mínimo 8 caracteres"
                  senha
                  visivel={senhaVisivel}
                  onAlternarVisivel={() => setSenhaVisivel((v) => !v)}
                  value={form.senha}
                  onChangeText={(v) => setField("senha", v)}
                  erro={errors.senha}
                />
                <Campo
                  label="Confirmar senha"
                  placeholder="Repita a senha"
                  senha
                  visivel={senhaVisivel}
                  onAlternarVisivel={() => setSenhaVisivel((v) => !v)}
                  value={form.confirmarSenha}
                  onChangeText={(v) => setField("confirmarSenha", v)}
                  erro={errors.confirmarSenha}
                />
                {erroGeral ? (
                  <View className="mb-3 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5">
                    <Text className="text-[13px] font-medium text-red-600">
                      {erroGeral}
                    </Text>
                  </View>
                ) : null}
                <Botao
                  label="Continuar"
                  onPress={() => {
                    if (validarEtapa1()) {
                      setErrors({});
                      setStep(2);
                    }
                  }}
                  className="mt-1 w-full"
                />
              </>
            ) : (
              <>
                <Campo
                  label="Modelo do carro"
                  placeholder="Ex.: Onix 1.0"
                  opcional
                  autoCapitalize="words"
                  value={form.modeloCarro}
                  onChangeText={(v) => setField("modeloCarro", v)}
                  erro={errors.modeloCarro}
                />
                <Campo
                  label="Placa"
                  placeholder="ABC1D23"
                  opcional
                  autoCapitalize="characters"
                  value={form.placa}
                  onChangeText={(v) => setField("placa", formatarPlaca(v))}
                  erro={errors.placa}
                />
                <Checkbox
                  checked={form.pcd}
                  onPress={() => setForm((p) => ({ ...p, pcd: !p.pcd }))}
                  label="Sou pessoa com deficiência (PCD)"
                  hint="Opcional. Declarar habilita a prioridade e a exclusividade das vagas PCD — sem a declaração, o sistema sempre atribui vaga Comum."
                />
                {erroGeral ? (
                  <View className="mb-3 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5">
                    <Text className="text-[13px] font-medium text-red-600">
                      {erroGeral}
                    </Text>
                  </View>
                ) : null}
                <Botao
                  label={loading ? "Criando conta…" : "Criar conta"}
                  onPress={async () => {
                    if (validarEtapa2()) await enviar();
                  }}
                  loading={loading}
                  className="mt-1 w-full"
                />
                <Botao
                  label="Pular esta etapa"
                  variant="fantasma"
                  onPress={enviar}
                  disabled={loading}
                  className="mt-2 w-full"
                />
                <Pressable
                  onPress={() => {
                    setErrors({});
                    setStep(1);
                  }}
                  className="mt-2 items-center py-1"
                >
                  <Text className="text-sm font-semibold text-slate-500">
                    ← Voltar
                  </Text>
                </Pressable>
              </>
            )}
          </View>

          <Text className="mt-5 text-center text-sm text-slate-500">
            Já tem conta?{" "}
            <Text className="font-bold text-blue-700" onPress={() => router.replace("/login")}>
              Entrar
            </Text>
          </Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function PassoEtapa({
  numero,
  ativo,
  concluido,
}: {
  numero: number;
  ativo: boolean;
  concluido: boolean;
}) {
  const fundo = concluido ? "bg-blue-600" : ativo ? "bg-blue-600" : "bg-slate-200";
  return (
    <View
      className={`h-6 w-6 items-center justify-center rounded-full ${fundo}`}
    >
      <Text className="text-[11px] font-bold text-white">
        {concluido ? "✓" : numero}
      </Text>
    </View>
  );
}
