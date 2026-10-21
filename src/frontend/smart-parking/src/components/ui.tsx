/**
 * Kit de primitivas visuais do SmartParking (NativeWind + RN puro, sem HTML).
 * Todas as telas (mobile e web) montam os templates do Figma com estas peças.
 */
import { ReactNode, useEffect, useRef } from "react";
import {
  ActivityIndicator,
  Animated,
  Easing,
  Modal,
  Pressable,
  ScrollView,
  StyleProp,
  Text,
  TextInput,
  TextInputProps,
  View,
  ViewStyle,
} from "react-native";
import { colors, ocupacaoColor } from "../theme";

// ---------------------------------------------------------- animações (RN core)
/**
 * Entrada suave (fade + leve subida) para listas e cards — usa só o
 * `Animated` do React Native (nenhuma dependência nova) e `useNativeDriver`,
 * que vale tanto no app (iOS/Android) quanto no web (wasm/JS driver).
 */
export function AnimarEntrada({
  children,
  delay = 0,
  distancia = 12,
}: {
  children: ReactNode;
  delay?: number;
  distancia?: number;
}) {
  const anim = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.timing(anim, {
      toValue: 1,
      duration: 320,
      delay,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: true,
    }).start();
  }, [anim, delay]);
  return (
    <Animated.View
      style={{
        opacity: anim,
        transform: [
          { translateY: anim.interpolate({ inputRange: [0, 1], outputRange: [distancia, 0] }) },
        ],
      }}
    >
      {children}
    </Animated.View>
  );
}

// ---------------------------------------------------------------- Logo
export function Logo({
  size = 40,
  tone = "blue",
}: {
  size?: number;
  tone?: "blue" | "white";
}) {
  const bg = tone === "blue" ? colors.primary : "#FFFFFF";
  const fg = tone === "blue" ? "#FFFFFF" : colors.primary;
  return (
    <View
      className="items-center justify-center rounded-xl"
      style={{ width: size, height: size, backgroundColor: bg }}
    >
      <Text
        className="font-extrabold text-white"
        style={{ color: fg, fontSize: size * 0.55, lineHeight: size * 0.7 }}
      >
        P
      </Text>
    </View>
  );
}

export function LogoBlox({ compact }: { compact?: boolean }) {
  return (
    <View className="flex-row items-center gap-2.5">
      <Logo size={compact ? 34 : 40} />
      <View>
        <Text
          className={`font-extrabold text-slate-900 ${compact ? "text-[15px]" : "text-base"}`}
        >
          Smart Parking
        </Text>
        <Text className="text-[11px] font-medium text-slate-500">Shoppings</Text>
      </View>
    </View>
  );
}

// ---------------------------------------------------------------- Botões
// Animated.Value SÓ pode viver no style de um componente Animated. Num
// <Pressable> comum, o objeto passa cru para o nativo e o Fabric derruba a
// tela com "Transform with key of 'scale' must be a number" (a web ignora e
// esconde o bug). createAnimatedComponent faz o wiring do driver nativo.
const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

type BotaoProps = {
  label: string;
  onPress?: () => void;
  variant?: "primario" | "contorno" | "fantasma" | "perigo" | "sucesso";
  disabled?: boolean;
  loading?: boolean;
  className?: string;
  style?: StyleProp<ViewStyle>;
  icon?: ReactNode;
};

export function Botao({
  label,
  onPress,
  variant = "primario",
  disabled,
  loading,
  className = "",
  style,
  icon,
}: BotaoProps) {
  // feedback tátil visual: mola de escala ao pressionar (web e nativo)
  const escala = useRef(new Animated.Value(1)).current;
  const apertar = (paraDentro: boolean) =>
    Animated.spring(escala, {
      toValue: paraDentro ? 0.96 : 1,
      friction: 5,
      tension: 120,
      useNativeDriver: true,
    }).start();

  const base = "flex-row items-center justify-center gap-2 rounded-xl px-5 py-3.5";
  const variants: Record<string, string> = {
    primario: "bg-blue-600 active:bg-blue-700",
    contorno: "border border-blue-600 bg-white active:bg-blue-50",
    fantasma: "bg-transparent",
    perigo: "bg-red-500 active:bg-red-600",
    sucesso: "bg-emerald-500 active:bg-emerald-600",
  };
  const labelColor: Record<string, string> = {
    primario: "text-white",
    contorno: "text-blue-700",
    fantasma: "text-blue-700",
    perigo: "text-white",
    sucesso: "text-white",
  };
  return (
    <AnimatedPressable
      accessibilityRole="button"
      onPress={onPress}
      onPressIn={() => apertar(true)}
      onPressOut={() => apertar(false)}
      disabled={disabled || loading}
      className={`${base} ${variants[variant]} ${
        disabled ? "opacity-40" : ""
      } ${className}`}
      style={[style, { transform: [{ scale: escala }] }]}
    >
      {loading ? (
        <ActivityIndicator
          size="small"
          color={variant === "contorno" || variant === "fantasma" ? colors.primary : "#fff"}
        />
      ) : (
        <>
          {icon}
          <Text className={`text-[15px] font-semibold ${labelColor[variant]}`}>
            {label}
          </Text>
        </>
      )}
    </AnimatedPressable>
  );
}

// ---------------------------------------------------------------- Card
export function Card({
  children,
  className = "",
  style,
}: {
  children: ReactNode;
  className?: string;
  style?: StyleProp<ViewStyle>;
}) {
  return (
    <View
      className={`rounded-2xl border border-slate-200 bg-white ${className}`}
      style={style}
    >
      {children}
    </View>
  );
}

export function TituloSecao({
  titulo,
  subtitulo,
  direita,
  aoVivo,
}: {
  titulo: string;
  subtitulo?: string;
  direita?: ReactNode;
  aoVivo?: boolean;
}) {
  return (
    <View className="mb-4 flex-row items-end justify-between">
      <View>
        <Text className="text-xl font-bold text-slate-900">{titulo}</Text>
        {subtitulo ? (
          <Text className="mt-0.5 text-sm text-slate-500">{subtitulo}</Text>
        ) : null}
      </View>
      <View className="flex-row items-center gap-3">
        {aoVivo ? <SeloAoVivo /> : null}
        {direita}
      </View>
    </View>
  );
}

export function SeloAoVivo() {
  // ponto pulsando — reforça visualmente que os dados são ao vivo
  const pulso = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulso, {
          toValue: 0.35,
          duration: 900,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.timing(pulso, {
          toValue: 1,
          duration: 900,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [pulso]);
  return (
    <View className="flex-row items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1">
      <Animated.View
        style={{ opacity: pulso }}
        className="h-1.5 w-1.5 rounded-full bg-emerald-500"
      />
      <Text className="text-[11px] font-semibold text-emerald-700">Ao vivo</Text>
    </View>
  );
}

// ---------------------------------------------------------------- Stat tile
export function StatTile({
  rotulo,
  valor,
  tone = "neutro",
  className = "",
}: {
  rotulo: string;
  valor: string;
  tone?: "neutro" | "verde" | "azul" | "vermelho" | "ambar" | "roxo";
  className?: string;
}) {
  const tones: Record<string, { bg: string; text: string }> = {
    neutro: { bg: "bg-slate-100", text: "text-slate-900" },
    verde: { bg: "bg-emerald-50", text: "text-emerald-600" },
    azul: { bg: "bg-blue-50", text: "text-blue-600" },
    vermelho: { bg: "bg-red-50", text: "text-red-500" },
    ambar: { bg: "bg-amber-50", text: "text-amber-600" },
    roxo: { bg: "bg-indigo-50", text: "text-indigo-600" },
  };
  const t = tones[tone];
  return (
    <View className={`items-start rounded-2xl p-4 ${t.bg} ${className}`}>
      <Text className="text-[13px] font-medium text-slate-500">{rotulo}</Text>
      <Text className={`mt-1 text-2xl font-extrabold ${t.text}`}>{valor}</Text>
    </View>
  );
}

// ---------------------------------------------------------------- Chip/Badge
export function Chip({
  label,
  tone = "neutro",
}: {
  label: string;
  tone?: "verde" | "vermelho" | "ambar" | "neutro" | "azul" | "vaga";
}) {
  const tones: Record<string, string> = {
    verde: "bg-emerald-100 text-emerald-700",
    vermelho: "bg-red-100 text-red-600",
    ambar: "bg-amber-100 text-amber-700",
    azul: "bg-blue-100 text-blue-700",
    neutro: "bg-slate-100 text-slate-600",
    vaga: "bg-slate-100 text-slate-500",
  };
  return (
    <View className={`self-start rounded-full px-2.5 py-1 ${tones[tone]}`}>
      <Text className={`text-[11px] font-semibold ${tones[tone].split(" ")[1]}`}>
        {label}
      </Text>
    </View>
  );
}

export function StatusVagaChip({ status }: { status: string }) {
  const map: Record<string, { dot: string; label: string; tone: "verde" | "vermelho" | "ambar" | "neutro" }> = {
    livre: { dot: "bg-emerald-500", label: "livre", tone: "verde" },
    ocupada: { dot: "bg-red-500", label: "ocupada", tone: "vermelho" },
    reservada: { dot: "bg-amber-400", label: "reservada", tone: "ambar" },
    inativa: { dot: "bg-slate-400", label: "inativa", tone: "neutro" },
  };
  const item = map[status] ?? map.inativa;
  return (
    <View className="flex-row items-center gap-1.5 self-start rounded-full bg-slate-100 px-2.5 py-1">
      <View className={`h-1.5 w-1.5 rounded-full ${item.dot}`} />
      <Text className="text-[11px] font-semibold capitalize text-slate-600">
        {item.label}
      </Text>
    </View>
  );
}

// ---------------------------------------------------------------- Barra ocupação
export function BarraOcupacao({ percentual }: { percentual: number }) {
  const largura = `${Math.max(2, Math.min(100, percentual))}%`;
  return (
    <View className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
      <View
        className="h-2.5 rounded-full"
        style={{ width: largura as any, backgroundColor: ocupacaoColor(percentual) }}
      />
    </View>
  );
}

// ---------------------------------------------------------------- Campo
interface CampoProps extends TextInputProps {
  label: string;
  helper?: string;
  erro?: string;
  senha?: boolean;
  opcional?: boolean;
  visivel?: boolean;
  onAlternarVisivel?: () => void;
}

export function Campo({
  label,
  erro,
  helper,
  senha,
  opcional,
  visivel,
  onAlternarVisivel,
  ...inputProps
}: CampoProps) {
  return (
    <View className="mb-4">
      <Text className="mb-1.5 text-[13px] font-semibold text-slate-700">
        {label}
        {opcional ? (
          <Text className="font-normal text-slate-400"> (opcional)</Text>
        ) : null}
      </Text>
      <View
        className={`flex-row items-center rounded-xl border-2 bg-slate-50 px-3.5 ${
          erro ? "border-red-300 bg-red-50" : "border-slate-200"
        }`}
      >
        <TextInput
          accessibilityLabel={label}
          placeholderTextColor="#94A3B8"
          secureTextEntry={senha && !visivel}
          className={`flex-1 py-3 text-base text-slate-900 ${
            erro ? "text-red-600" : "text-slate-900"
          }`}
          {...inputProps}
        />
        {senha ? (
          <Pressable onPress={onAlternarVisivel} hitSlop={8}>
            <Text className="pl-2 text-xs font-semibold text-blue-600">
              {visivel ? "Ocultar" : "Mostrar"}
            </Text>
          </Pressable>
        ) : null}
      </View>
      {helper && !erro ? (
        <Text className="mt-1 text-[11px] text-slate-400">{helper}</Text>
      ) : null}
      <Text className="mt-1 min-h-[16px] text-xs text-red-600">{erro ?? ""}</Text>
    </View>
  );
}

// ---------------------------------------------------------------- Pills piso
export function PillsAndares({
  andares,
  selecionado,
  onSelect,
}: {
  andares: number[];
  selecionado: number | null;
  onSelect: (andar: number) => void;
}) {
  return (
    <View className="flex-row flex-wrap gap-2">
      {andares.map((andar) => {
        const ativo = selecionado === andar;
        return (
          <Pressable
            key={andar}
            onPress={() => onSelect(andar)}
            className={`rounded-full border px-4 py-2 ${
              ativo ? "border-blue-600 bg-blue-600" : "border-slate-200 bg-white"
            }`}
          >
            <Text
              className={`text-[13px] font-semibold ${
                ativo ? "text-white" : "text-slate-600"
              }`}
            >
              {andar}º andar
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

// ---------------------------------------------------------------- Legenda
export function LegendaVagas({
  itens,
}: {
  itens?: { cor: string; rotulo: string }[];
}) {
  const padrao = [
    { cor: colors.vagaLivre, rotulo: "Livre" },
    { cor: colors.vagaOcupada, rotulo: "Ocupada" },
    { cor: "#F59E0B", rotulo: "Reservada" },
    { cor: colors.vagaInativa, rotulo: "Inativa" },
  ];
  const lista = itens ?? padrao;
  return (
    <View className="flex-row flex-wrap items-center gap-x-4 gap-y-1">
      {lista.map((i) => (
        <View key={i.rotulo} className="flex-row items-center gap-1.5">
          <View className="h-2 w-2 rounded-full" style={{ backgroundColor: i.cor }} />
          <Text className="text-xs text-slate-500">{i.rotulo}</Text>
        </View>
      ))}
    </View>
  );
}

// ---------------------------------------------------------------- Estados
export function BlocoCarregando({ label = "Carregando…" }: { label?: string }) {
  return (
    <View className="items-center gap-3 py-16">
      <ActivityIndicator size="large" color={colors.primary} />
      <Text className="text-sm text-slate-500">{label}</Text>
    </View>
  );
}

export function BlocoErro({
  titulo = "Algo deu errado",
  descricao,
  acaoLabel = "Tentar de novo",
  onAcao,
}: {
  titulo?: string;
  descricao?: string | null;
  acaoLabel?: string;
  onAcao?: () => void;
}) {
  return (
    <Card className="items-center gap-3 p-8">
      <Text className="text-3xl">🚧</Text>
      <Text className="text-base font-bold text-slate-900">{titulo}</Text>
      {descricao ? (
        <Text className="text-center text-sm text-slate-500">{descricao}</Text>
      ) : null}
      {onAcao ? <Botao label={acaoLabel} onPress={onAcao} variant="contorno" /> : null}
    </Card>
  );
}

export function BlocoVazio({
  emoji = "🅿️",
  titulo,
  descricao,
  acaoLabel,
  onAcao,
}: {
  emoji?: string;
  titulo: string;
  descricao?: string;
  acaoLabel?: string;
  onAcao?: () => void;
}) {
  return (
    <Card className="items-center gap-3 p-8">
      <Text className="text-4xl">{emoji}</Text>
      <Text className="text-base font-bold text-slate-900">{titulo}</Text>
      {descricao ? (
        <Text className="text-center text-sm text-slate-500">{descricao}</Text>
      ) : null}
      {acaoLabel && onAcao ? (
        <Botao label={acaoLabel} onPress={onAcao} className="mt-1" />
      ) : null}
    </Card>
  );
}

// ---------------------------------------------------------------- Util
export function formatarMinutos(min: number | undefined | null): string {
  if (!min || min <= 0) return "—";
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  if (h <= 0) return `${m} min`;
  return m > 0 ? `${h}h ${m}min` : `${h}h`;
}

export function formatarMoedaBR(valor: number | undefined | null): string {
  if (valor == null) return "—";
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

// ---------------------------------------------------------------- Modal de formulário
/**
 * Modal genérico para cadastros do painel (novo estacionamento, andar, lote de
 * vagas, usuário). Fundo tocável para fechar + footer padronizado com botão
 * de confirmar (com estado de loading) — usa só o Modal do RN.
 */
export function ModalForma({
  visivel,
  titulo,
  descricao,
  aoFechar,
  aoConfirmar,
  rotuloConfirmar = "Salvar",
  ocupado = false,
  children,
}: {
  visivel: boolean;
  titulo: string;
  descricao?: string;
  aoFechar: () => void;
  aoConfirmar: () => void;
  rotuloConfirmar?: string;
  ocupado?: boolean;
  children: ReactNode;
}) {
  return (
    <Modal
      visible={visivel}
      transparent
      animationType="fade"
      onRequestClose={aoFechar}
      statusBarTranslucent
    >
      <View className="flex-1 items-center justify-center bg-black/50 p-4">
        <Pressable accessibilityRole="button" onPress={aoFechar} className="absolute inset-0" />
        <View className="w-full max-w-md">
          <Card className="overflow-hidden p-5">
            <Text className="text-lg font-extrabold text-slate-900">{titulo}</Text>
            {descricao ? (
              <Text className="mt-0.5 text-[13px] text-slate-500">{descricao}</Text>
            ) : null}
            <ScrollView style={{ maxHeight: 420 }} className="mt-4">
              {children}
            </ScrollView>
            <View className="mt-5 flex-row gap-2">
              <Botao
                label="Cancelar"
                variant="contorno"
                onPress={aoFechar}
                className="flex-1"
              />
              <Botao
                label={rotuloConfirmar}
                onPress={aoConfirmar}
                loading={ocupado}
                className="flex-1"
              />
            </View>
          </Card>
        </View>
      </View>
    </Modal>
  );
}
