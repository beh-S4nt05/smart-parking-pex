import { pagina } from "../styles/recipes";
/**
 * Cadastro em 2 etapas (dados pessoais + veículo opcional), agora integrado:
 * POST /auth/registrar → auto-login via /auth/login → redireciona por papel.
 * Mantém o fluxo existente, com a paleta azul dos templates do Figma.
 */
import { useRef, useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../hooks/useAuth";
import { apiErrorMessage } from "../services/api";
import { Botao, Campo, IconeCheck, IconeVoltar, Logo } from "../components/ui";
import OptionChips from "../components/OptionChips";
import type { CategoriaVeiculo, MotorizacaoVeiculo } from "../types/api";

type FormState = {
  nome: string;
  email: string;
  telefone: string;
  senha: string;
  confirmarSenha: string;
  modeloCarro: string;
  placa: string;
  categoria: CategoriaVeiculo;
  motorizacao: MotorizacaoVeiculo;
  beneficio: "nenhum" | "idoso" | "pcd";
  dataNascimento: string;
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
    categoria: "carro",
    motorizacao: "combustao",
    beneficio: "nenhum",
    dataNascimento: "",
});
  const [errors, setErrors] = useState<FormErrors>({});
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [senhaVisivel, setSenhaVisivel] = useState(false);
  const [mostrarLoginAposErro, setMostrarLoginAposErro] = useState(false);
  // Bloqueia toques muito rápidos antes de o React renderizar loading=true.
  const envioEmCurso = useRef(false);

  function setField<K extends keyof FormState>(key: K, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => ({ ...prev, [key]: undefined }));
    setErroGeral(null);
    setMostrarLoginAposErro(false);
  }

  function validarEtapa1() {
    const e: FormErrors = {};
    if (form.nome.trim().length < 2) e.nome = "Informe seu nome (mínimo 2 caracteres)";
    if (!form.email.trim()) e.email = "Informe o e-mail";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) e.email = "Digite um e-mail válido";

    const tel = form.telefone.replace(/\D/g, "");
    if (!tel) e.telefone = "Informe seu telefone";
    else if (tel.length !== 10 && tel.length !== 11)
      e.telefone = "Use DDD + telefone (10 ou 11 dígitos)";

    if (!form.senha) e.senha = "Informe a senha";
    else if (form.senha.length < 8) e.senha = "A senha precisa de pelo menos 8 caracteres";

    if (!form.confirmarSenha) e.confirmarSenha = "Confirme sua senha";
    else if (form.confirmarSenha !== form.senha)
      e.confirmarSenha = "As senhas não coincidem";

    setErrors(e);
    return Object.keys(e).length === 0;
  }

  function validarEtapa2() {
    const e: FormErrors = {};
    if (form.modeloCarro.trim() && !form.placa.trim()) {
      e.placa = "Informe a placa para cadastrar o veículo";
    }
    if (form.placa.trim() && !placaValida(form.placa)) {
      e.placa = "Placa inválida (ex.: ABC1D23)";
    }
    if (form.dataNascimento.trim()) {
      const [dia, mes, ano] = form.dataNascimento.split("/").map(Number);
      const dt = new Date(Date.UTC(ano, mes - 1, dia));
      if (!/^[0-9]{2}\/[0-9]{2}\/[0-9]{4}$/.test(form.dataNascimento) ||
          dt.getUTCFullYear() !== ano || dt.getUTCMonth() !== mes - 1 || dt.getUTCDate() !== dia ||
          dt > new Date()) {
        e.dataNascimento = "Informe uma data válida: DD/MM/AAAA";
      } else if (form.beneficio === "idoso") {
        const hoje = new Date();
        const idade = hoje.getFullYear() - ano -
          (hoje.getMonth() + 1 < mes || (hoje.getMonth() + 1 === mes && hoje.getDate() < dia) ? 1 : 0);
        if (idade < 60) e.dataNascimento = "Credencial de idoso exige 60 anos ou mais";
      }
    } else if (form.beneficio === "idoso") {
      e.dataNascimento = "Informe o nascimento para solicitar benefício de idoso";
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  function dataISO() {
    if (!form.dataNascimento) return undefined;
    const [dia, mes, ano] = form.dataNascimento.split("/");
    return `${ano}-${mes}-${dia}`;
  }

  async function enviar(pularOpcionais = false) {
    if (envioEmCurso.current) return;
    // Previne envio com etapa 1 incompleta em qualquer fluxo de navegação.
    if (!validarEtapa1()) {
      setStep(1);
      return;
    }
    envioEmCurso.current = true;
    setLoading(true);
    setErroGeral(null);
    setMostrarLoginAposErro(false);
    let contaCriada = false;
    try {
      const comVeiculo = !pularOpcionais && Boolean(form.placa.trim());
      await register({
        nome: form.nome.trim(),
        email: form.email.trim().toLowerCase(),
        senha: form.senha,
        telefone: form.telefone.replace(/\D/g, ""),
        data_nascimento: pularOpcionais ? undefined : dataISO(),
        beneficio_solicitado: pularOpcionais || form.beneficio === "nenhum" ? undefined : form.beneficio,
        is_pcd: false, // verificação documental pendente; não habilitar vaga especial sem análise
        veiculo: comVeiculo ? {
          placa: formatarPlaca(form.placa),
          categoria: form.categoria,
          motorizacao: form.motorizacao,
          modelo: form.modeloCarro.trim() || undefined,
        } : undefined,
      });
      contaCriada = true;
      await signIn(form.email.trim().toLowerCase(), form.senha);
      router.replace("/");
    } catch (err) {
      const motivo = apiErrorMessage(err, "Não foi possível concluir o cadastro.");
      const duplicado = [400, 409].includes(
        (err as { response?: { status?: number } })?.response?.status ?? 0,
      ) && /e-mail.*cadastrad|e-mail.*conta/i.test(motivo);
      setMostrarLoginAposErro(contaCriada || duplicado);
      setErroGeral(
        contaCriada
          ? "Sua conta foi criada! O acesso automático não terminou. Entre usando o e-mail e a senha cadastrados; não repita o cadastro."
          : duplicado
            ? "Este e-mail já possui uma conta. Entre com sua senha ou use a recuperação de acesso."
            : motivo,
      );
    } finally {
      envioEmCurso.current = false;
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      className={pagina}
      style={Platform.OS === "web" ? undefined : { backgroundColor: "#F3F7FD" }}
    >
      <ScrollView contentContainerStyle={Platform.OS === "web" ? { flexGrow: 1, justifyContent: "center" } : { flexGrow: 1, paddingBottom: 32 }} keyboardShouldPersistTaps="handled">
        <View className="w-full max-w-[440px] self-center px-5 py-10 3xl:max-w-[520px] 3xl:py-14" style={Platform.OS === "web" ? undefined : { paddingTop: 20, maxWidth: 500 }}>
          <Pressable
            onPress={() => router.replace("/")}
            accessibilityRole="button"
            accessibilityLabel="Voltar ao início sem criar conta"
            className="mb-5 min-h-11 flex-row items-center gap-2 self-start rounded-lg px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            style={Platform.OS === "web" ? undefined : { borderWidth: 0, paddingHorizontal: 0, marginBottom: 15 }}
          >
            <IconeVoltar />
            <Text className="text-sm font-semibold text-blue-700">Início</Text>
          </Pressable>
          {Platform.OS === "web" ? (
            <View className="mb-6 items-center">
              <Logo size={48} />
              <Text className="mt-3 text-2xl font-extrabold text-slate-900">Criar conta</Text>
              <Text className="mt-1 text-center text-sm text-slate-600">
                {step === 1 ? "Vamos começar com seus dados pessoais" : "Se quiser, cadastre seu veículo agora"}
              </Text>
            </View>
          ) : (
            <View style={{ backgroundColor: "#0F1E38", padding: 20, borderRadius: 23, marginBottom: 22 }}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 11, marginBottom: 16 }}>
                <View style={{ width: 43, height: 43, borderRadius: 13, backgroundColor: "#2563EB", justifyContent: "center", alignItems: "center" }}>
                  <Ionicons name="car-sport" size={25} color="#FFFFFF" />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={{ color: "#FFFFFF", fontSize: 17, fontWeight: "800" }}>Smart Parking</Text>
                  <Text style={{ color: "#ADC3E0", fontSize: 11 }}>Sua jornada começa aqui</Text>
                </View>
              </View>
              <Text style={{ color: "#FFFFFF", fontSize: 25, fontWeight: "900" }}>Criar conta</Text>
              <Text style={{ color: "#C0D0E8", fontSize: 13, marginTop: 6, lineHeight: 19 }}>
                {step === 1 ? "Primeiro, precisamos conhecer você." : "Agora, personalize sua experiência."}
              </Text>
            </View>
          )}

          {/* Gradiente de objetivo: etapa explícita + barra preenchida.
              O usuário vê o quanto falta e não abandona no meio. */}
          <View className="mb-3 flex-row items-center justify-between px-1">
            <Text className="text-[13px] font-bold text-slate-800">
              Etapa {step} de 2
            </Text>
            <Text className="text-[12px] font-semibold text-blue-700">
              {step === 1 ? "Comece aqui" : "Quase pronto"}
            </Text>
          </View>
          <View className="sp-progresso mb-4">
            <View
              className="sp-progresso-fill"
              style={{ width: step === 1 ? "50%" : "100%" }}
            />
          </View>
          {Platform.OS === "web" ? <>
            <View className="mb-2 flex-row items-center gap-2 px-1">
            <PassoEtapa numero={1} ativo={step === 1} concluido={step > 1} />
            <View
              className={`h-0.5 flex-1 ${step > 1 ? "bg-blue-600" : "bg-slate-200"}`}
            />
            <PassoEtapa numero={2} ativo={step === 2} concluido={false} />
          </View>
          <View className="mb-5 flex-row justify-between px-1">
            <Text
              className={`text-[11px] font-semibold ${step === 1 ? "text-blue-700" : "text-slate-600"}`}
            >
              Seus dados
            </Text>
            <Text
              className={`text-[11px] font-semibold ${step === 2 ? "text-blue-700" : "text-slate-600"}`}
            >
              Seu veículo (opcional)
            </Text>
          </View>
          </> : (
            <View style={{ marginBottom: 17, flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
              <Text style={{ color: "#15233B", fontWeight: "800", fontSize: 15 }}>{step === 1 ? "Dados pessoais" : "Dados do veículo"}</Text>
              <Text style={{ color: "#64748B", fontSize: 12 }}>{step === 1 ? "1/2" : "2/2"}</Text>
            </View>
          )}

          <View className="rounded-2xl border border-slate-200 bg-white p-6" style={Platform.OS === "web" ? undefined : { borderWidth: 0, borderRadius: 21, padding: 19 }}>
            {step === 1 ? (
              <>
                <Campo
                  label="Nome completo"
                  placeholder="Seu nome"
                  autoCapitalize="words"
                  autoComplete="name"
                  value={form.nome}
                  onChangeText={(v) => setField("nome", v)}
                  erro={errors.nome}
                />
                <Campo
                  label="E-mail"
                  placeholder="voce@email.com"
                  keyboardType="email-address"
                  autoComplete="email"
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
                  autoComplete="tel"
                  value={form.telefone}
                  onChangeText={(v) => setField("telefone", formatarTelefone(v))}
                  erro={errors.telefone}
                />
                <Campo
                  label="Senha"
                  placeholder="Mínimo 8 caracteres"
                  helper="Use uma senha exclusiva para sua conta."
                  autoComplete="new-password"
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
                  autoComplete="new-password"
                  senha
                  visivel={senhaVisivel}
                  onAlternarVisivel={() => setSenhaVisivel((v) => !v)}
                  value={form.confirmarSenha}
                  onChangeText={(v) => setField("confirmarSenha", v)}
                  erro={errors.confirmarSenha}
                />
                {erroGeral ? (
                  <View className="mb-3 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5">
                    <Text accessibilityRole="alert" className="text-[13px] font-medium text-red-600">
                      {erroGeral}
                    </Text>
                    {mostrarLoginAposErro ? (
                      <Botao label="Ir para entrar" variant="contorno"
                        onPress={() => router.replace("/login")} className="mt-2 w-full" />
                    ) : null}
                  </View>
                ) : null}
                <Botao
                  label="Continuar"
                  disabled={loading}
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
                <Text style={{ fontSize: 17, fontWeight: "800", color: "#17243B", marginBottom: 7 }}>Seu veículo</Text>
                <Text style={{ color: "#64748B", fontSize: 12, marginBottom: 16 }}>
                  Esta etapa é opcional. Você pode incluir veículos e solicitar credenciais depois, pelo perfil.
                </Text>
                <OptionChips
                  label="Tipo do veículo"
                  value={form.categoria}
                  onChange={(categoria) => setForm((p) => ({ ...p, categoria }))}
                  options={[{ value: "carro", label: "Carro" }, { value: "moto", label: "Moto" }]}
                />
                <OptionChips
                  label="Motorização"
                  value={form.motorizacao}
                  onChange={(motorizacao) => setForm((p) => ({ ...p, motorizacao }))}
                  options={[
                    { value: "combustao", label: "Combustão" },
                    { value: "hibrido", label: "Híbrido" },
                    { value: "eletrico", label: "Elétrico" },
                  ]}
                />
                <Campo
                  label="Modelo do veículo"
                  placeholder={form.categoria === "moto" ? "Ex.: Honda CG 160" : "Ex.: Onix 1.0"}
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
                <View style={{ borderTopWidth: 1, borderColor: "#EDF2F7", paddingTop: 18, marginTop: 3 }}>
                  <Text style={{ fontSize: 17, fontWeight: "800", color: "#17243B", marginBottom: 6 }}>Vaga especial</Text>
                  <Text style={{ fontSize: 12, color: "#64748B", lineHeight: 18, marginBottom: 16 }}>
                    Somente se precisar. A solicitação exige credencial oficial e análise; não libera vagas especiais automaticamente.
                  </Text>
                  <OptionChips
                    label="Deseja solicitar validação?"
                    value={form.beneficio}
                    onChange={(beneficio) => setForm((p) => ({ ...p, beneficio }))}
                    options={[
                      { value: "nenhum", label: "Não preciso" },
                      { value: "idoso", label: "Idoso (60+)" },
                      { value: "pcd", label: "PCD" },
                    ]}
                  />
                  {form.beneficio === "idoso" ? (
                    <Campo
                      label="Data de nascimento"
                      placeholder="DD/MM/AAAA"
                      keyboardType="number-pad"
                      value={form.dataNascimento}
                      onChangeText={(v) => {
                        const numeros = v.replace(/\D/g, "").slice(0, 8);
                        const formatado = numeros.length <= 2 ? numeros :
                          numeros.length <= 4 ? `${numeros.slice(0, 2)}/${numeros.slice(2)}` :
                          `${numeros.slice(0, 2)}/${numeros.slice(2, 4)}/${numeros.slice(4)}`;
                        setField("dataNascimento", formatado);
                      }}
                      erro={errors.dataNascimento}
                    />
                  ) : null}
                  {form.beneficio !== "nenhum" ? (
                    <View style={{ backgroundColor: "#EFF6FF", borderRadius: 12, padding: 12, marginBottom: 16 }}>
                      <Text style={{ color: "#1E40AF", fontSize: 12, lineHeight: 19 }}>
                        Solicitação registrada como pendente. A autorização dependerá da conferência da credencial oficial por responsável habilitado.
                      </Text>
                    </View>
                  ) : null}
                </View>
                {erroGeral ? (
                  <View className="mb-3 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5">
                    <Text accessibilityRole="alert" className="text-[13px] font-medium text-red-600">
                      {erroGeral}
                    </Text>
                    {mostrarLoginAposErro ? (
                      <Botao label="Ir para entrar" variant="contorno"
                        onPress={() => router.replace("/login")} className="mt-2 w-full" />
                    ) : null}
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
                  label="Cadastrar sem opcionais"
                  variant="fantasma"
                  onPress={() => enviar(true)}
                  disabled={loading}
                  className="mt-2 w-full"
                />
                <Pressable
                  onPress={() => {
                    if (loading) return;
                    setErrors({});
                    setStep(1);
                  }}
                  disabled={loading}
                  accessibilityRole="button"
                  accessibilityLabel="Voltar à etapa anterior"
                  hitSlop={4}
                  className="mt-2 min-h-11 w-full items-center justify-center py-1"
                >
                  <View className="flex-row items-center gap-2">
                    <IconeVoltar />
                    <Text className="text-sm font-semibold text-slate-600">Voltar</Text>
                  </View>
                </Pressable>
              </>
            )}
          </View>

          <Text className="mt-5 text-center text-sm text-slate-600">
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
  const fundo = concluido || ativo ? "bg-blue-600" : "bg-slate-200";
  return (
    <View
      className={`h-9 w-9 items-center justify-center rounded-full border-2 border-white shadow-sm ${fundo}`}
    >
      {concluido ? (
        <IconeCheck cor="#FFFFFF" tamanho={14} />
      ) : (
        <Text className={`text-sm font-bold ${ativo ? "text-white" : "text-slate-600"}`}>
          {numero}
        </Text>
      )}
    </View>
  );
}
