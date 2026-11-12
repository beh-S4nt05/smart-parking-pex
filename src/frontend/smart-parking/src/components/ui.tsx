/**
 * Kit de primitivas visuais do SmartParking (NativeWind + RN puro, sem HTML).
 * Todas as telas (mobile e web) montam os templates do Figma com estas peças.
 */
import { ComponentProps, ReactNode, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  Easing,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleProp,
  Text,
  TextInput,
  TextInputProps,
  View,
  ViewStyle,
  useWindowDimensions,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors, ocupacaoColor } from "../theme";
import { useMovimentoReduzido } from "../hooks/useMovimentoReduzido";

// ---------------------------------------------------------- animações (RN core)
/**
 * Entrada suave (fade + leve subida) para listas e cards — usa só o
 * `Animated` do React Native (nenhuma dependência nova). `useNativeDriver`
 * SÓ existe no nativo — na web é sempre driver JS (na web `true` dispara o
 * warning "native animated module is missing" no console; correção da
 * auditoria de 22/10 rod.7). Onde a animação roda nas duas plataformas
 * (Botao, SeloAoVivo, ModalForma) o flag é `Platform.OS !== "web"`.
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
  const reduzido = useMovimentoReduzido();
  useEffect(() => {
    // Web entra limpo (evita SSR com opacity:0); movimento reduzido também.
    if (Platform.OS === "web" || reduzido) return;
    Animated.timing(anim, {
      toValue: 1,
      duration: 320,
      delay,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: true,
    }).start();
  }, [anim, delay, reduzido]);
  if (Platform.OS === "web" || reduzido) return <>{children}</>;
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
/**
 * Fade rapido (130ms) para TROCA de conteudo — abas do painel etc. Mais seco
 * que AnimarEntrada de proposito: trocar aba e acao repetitiva.
 */
export function FadeTroca({
  children,
  chave,
}: {
  children: ReactNode;
  chave: string;
}) {
  const anim = useRef(new Animated.Value(0)).current;
  const reduzido = useMovimentoReduzido();
  useEffect(() => {
    // Troca de aba sem fade na web (SSR-safe) e com movimento reduzido.
    if (Platform.OS === "web" || reduzido) return;
    anim.setValue(0);
    Animated.timing(anim, {
      toValue: 1,
      duration: 130,
      easing: Easing.out(Easing.quad),
      useNativeDriver: true,
    }).start();
  }, [anim, chave, reduzido]);
  if (Platform.OS === "web" || reduzido) return <>{children}</>;
  return <Animated.View style={{ opacity: anim }}>{children}</Animated.View>;
}

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
        <Text className="text-[11px] font-medium text-slate-600">Shoppings</Text>
      </View>
    </View>
  );
}

// ---------------------------------------------------------------- Ícones desenhados
/**
 * Glifos Unicode (☰, ✕, ←, ⚠️) não têm cobertura garantida nas fontes do
 * navegador/aparelho: medimos botões com 44px que apareciam VAZIOS no
 * Chromium e no celular. Estes ícones usam só Views com cor de fundo/borda,
 * então renderizam em qualquer plataforma, com ou sem fonte carregada.
 */
export function IconeMenu({ aberto = false, cor = "#334155" }: { aberto?: boolean; cor?: string }) {
  const barra = { backgroundColor: cor } as const;
  if (aberto) return <IconeFechar cor={cor} tamanho={16} />;
  return (
    <View className="h-4 w-4 items-center justify-center gap-[3px]">
      <View className="h-[2px] w-4 rounded-full" style={barra} />
      <View className="h-[2px] w-4 rounded-full" style={barra} />
      <View className="h-[2px] w-4 rounded-full" style={barra} />
    </View>
  );
}

export function IconeFechar({ cor = "#334155", tamanho = 16 }: { cor?: string; tamanho?: number }) {
  return (
    <View className="items-center justify-center" style={{ width: tamanho, height: tamanho }}>
      <View
        className="absolute rounded-full"
        style={{ width: tamanho, height: 2, backgroundColor: cor, transform: [{ rotate: "45deg" }] }}
      />
      <View
        className="absolute rounded-full"
        style={{ width: tamanho, height: 2, backgroundColor: cor, transform: [{ rotate: "-45deg" }] }}
      />
    </View>
  );
}

export function IconeChevron({
  aberto = false,
  cor = "#2563EB",
  tamanho = 10,
}: {
  aberto?: boolean;
  cor?: string;
  tamanho?: number;
}) {
  return (
    <View className="items-center justify-center" style={{ width: tamanho + 4, height: tamanho + 4 }}>
      <View
        style={{
          width: tamanho,
          height: tamanho,
          borderRightWidth: 2,
          borderBottomWidth: 2,
          borderColor: cor,
          borderRadius: 1,
          transform: [{ rotate: aberto ? "225deg" : "45deg" }],
        }}
      />
    </View>
  );
}

export function IconeCheck({ cor = "#FFFFFF", tamanho = 11 }: { cor?: string; tamanho?: number }) {
  return (
    <View className="items-center justify-center" style={{ width: tamanho + 2, height: tamanho + 2 }}>
      <View
        style={{
          width: tamanho * 0.5,
          height: tamanho * 0.85,
          borderRightWidth: 2,
          borderBottomWidth: 2,
          borderColor: cor,
          borderRadius: 1,
          transform: [{ rotate: "45deg" }],
        }}
      />
    </View>
  );
}

export function IconeVoltar({
  cor = "#2563EB",
  tamanho = 14,
}: {
  cor?: string;
  tamanho?: number;
}) {
  return (
    <View className="items-center justify-center" style={{ width: tamanho, height: tamanho }}>
      <View
        className="absolute rounded-full"
        style={{ width: tamanho, height: 2, backgroundColor: cor }}
      />
      <View
        className="absolute"
        style={{
          left: 0,
          width: tamanho * 0.55,
          height: tamanho * 0.55,
          borderLeftWidth: 2,
          borderBottomWidth: 2,
          borderColor: cor,
          borderRadius: 1,
          transform: [{ rotate: "45deg" }],
        }}
      />
    </View>
  );
}

// ---------------------------------------------------------------- Botões
// Animated.Value SÓ pode viver no style de um componente Animated. Num
// <Pressable> comum, o objeto passa cru para o nativo e o Fabric derruba a
// tela com "Transform with key of 'scale' must be a number" (crash do PR#7).
// Na WEB, porém, o createAnimatedComponent é invisível ao css-interop do
// NativeWind e DERRUBAVA o className inteiro — medido no HTML pré-render do
// `expo export web`: <button> sem bg/padding = "botão invisível". Duas rotas:
//   · web    → Pressable puro + feedback por CSS :active (0 JS, 0 flash);
//   · nativo → Animated (guarda do crash Fabric).
const PressavelAnimada =
  Platform.OS === "web" ? Pressable : Animated.createAnimatedComponent(Pressable);

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
  const ehWeb = Platform.OS === "web";
  const reduzido = useMovimentoReduzido();
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  useEffect(() => {
    if (reduzido) escala.setValue(1);
  }, [escala, reduzido]);
  const apertar = (paraDentro: boolean) => {
    if (ehWeb || reduzido) return; // sem mola quando o sistema pede menos movimento
    Animated.spring(escala, {
      toValue: paraDentro ? 0.96 : 1,
      // calibrado p/ ~140ms de feedback (auditoria de animacao 22/10):
      // wobble longo atrasa a percepcao de resposta ao toque
      friction: 7,
      tension: 180,
      useNativeDriver: true,
    }).start();
  };

  const base =
    "relative min-h-11 flex-row select-none items-center justify-center gap-2 rounded-xl px-5 py-3.5";
  const variants: Record<string, string> = {
    primario: "bg-blue-600 hover:bg-blue-700 active:bg-blue-800",
    contorno: "border border-blue-600 bg-white hover:bg-blue-50 active:bg-blue-100",
    fantasma: "bg-transparent hover:bg-blue-100/70 active:bg-blue-200/70",
    perigo: "bg-red-600 hover:bg-red-700 active:bg-red-800",
    // emerald-600 não atinge 4,5:1 com texto branco; 700 atinge 5,48:1.
    sucesso: "bg-emerald-700 hover:bg-emerald-800 active:bg-emerald-900",
  };
  const labelColor: Record<string, string> = {
    primario: "text-white",
    contorno: "text-blue-600",
    fantasma: "text-blue-600",
    perigo: "text-white",
    sucesso: "text-white",
  };
  const labelEmDestaque =
    ehWeb && (hovered || focused) && (variant === "contorno" || variant === "fantasma");
  return (
    <PressavelAnimada
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: Boolean(disabled || loading), busy: Boolean(loading) }}
      {...(ehWeb
        ? {
            "aria-busy": Boolean(loading),
            "aria-disabled": Boolean(disabled || loading),
            onHoverIn: () => setHovered(true),
            onHoverOut: () => setHovered(false),
            onFocus: () => setFocused(true),
            onBlur: () => setFocused(false),
          }
        : {})}
      onPress={onPress}
      {...(ehWeb || reduzido
        ? {}
        : { onPressIn: () => apertar(true), onPressOut: () => apertar(false) })}
      hitSlop={{ top: 4, bottom: 4, left: 8, right: 8 }}
      disabled={disabled || loading}
      className={`${base} ${variants[variant]} ${
        disabled ? "opacity-40" : ""
      } ${ehWeb
        ? "transition-all duration-150 ease-out active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 motion-reduce:transform-none motion-reduce:transition-none motion-reduce:hover:transform-none motion-reduce:active:transform-none"
        : ""} ${className}`}
      style={ehWeb || reduzido ? style : [style, { transform: [{ scale: escala }] }]}
    >
      <View
        className={`flex-row items-center justify-center gap-2 ${loading ? "opacity-0" : ""}`}
      >
        {icon}
        <Text
          className={`text-[15px] font-semibold ${labelColor[variant]} ${
            ehWeb ? "transition-colors duration-150 ease-out motion-reduce:transition-none" : ""
          }`}
          style={labelEmDestaque ? { color: colors.primaryDark } : undefined}
        >
          {label}
        </Text>
      </View>
      {loading ? (
        <View pointerEvents="none" className="absolute inset-0 items-center justify-center">
          <ActivityIndicator
            size="small"
            color={variant === "contorno" || variant === "fantasma" ? colors.primary : "#fff"}
          />
        </View>
      ) : null}
    </PressavelAnimada>
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
          <Text className="mt-0.5 text-sm text-slate-600">{subtitulo}</Text>
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
  // ponto pulsando — reforça visualmente que os dados são ao vivo, mas fica
  // estático quando o usuário pede menos movimento.
  const pulso = useRef(new Animated.Value(1)).current;
  const reduzido = useMovimentoReduzido();
  useEffect(() => {
    if (reduzido) {
      pulso.setValue(1);
      return;
    }
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulso, {
          toValue: 0.35,
          duration: 900,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: Platform.OS !== "web",
        }),
        Animated.timing(pulso, {
          toValue: 1,
          duration: 900,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: Platform.OS !== "web",
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [pulso, reduzido]);
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
      <Text className="text-[13px] font-medium text-slate-600">{rotulo}</Text>
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
    vaga: "bg-slate-100 text-slate-600",
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
  const descricao = erro ?? helper;
  const invalido = Boolean(erro);
  const desabilitado = inputProps.editable === false;
  return (
    <View className="mb-4">
      <Text className="mb-1.5 text-[13px] font-semibold text-slate-700">
        {label}
        {opcional ? (
          <Text className="font-normal text-slate-600"> (opcional)</Text>
        ) : null}
      </Text>
      <View
        className={`min-w-0 flex-row items-center rounded-xl border-2 bg-slate-50 px-3.5 ${
          erro ? "border-red-300 bg-red-50" : "border-slate-200"
        }`}
      >
        <TextInput
          accessibilityLabel={label}
          accessibilityHint={descricao}
          accessibilityState={{ disabled: desabilitado }}
          placeholderTextColor="#64748B"
          secureTextEntry={senha && !visivel}
          className={`min-w-0 flex-1 py-3 text-base ${
            erro ? "text-red-600" : "text-slate-900"
          }`}
          {...(Platform.OS === "web"
            ? {
                "aria-invalid": invalido ? "true" : "false",
                "aria-required": opcional ? "false" : "true",
              }
            : {})}
          {...inputProps}
        />
        {senha ? (
          <Pressable
            onPress={onAlternarVisivel}
            disabled={!onAlternarVisivel}
            hitSlop={8}
            accessibilityRole="button"
            accessibilityLabel={visivel ? "Ocultar senha" : "Mostrar senha"}
            accessibilityHint="Alterna a visualização da senha digitada"
            accessibilityState={{ disabled: !onAlternarVisivel }}
            className="min-h-11 min-w-11 flex-row items-center justify-center rounded-md px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <Text className="text-xs font-semibold text-blue-600">
              {visivel ? "Ocultar" : "Mostrar"}
            </Text>
          </Pressable>
        ) : null}
      </View>
      {helper && !erro ? (
        <Text className="mt-1 text-[11px] text-slate-600">{helper}</Text>
      ) : null}
      <Text
        accessibilityRole={erro ? "alert" : undefined}
        accessibilityLiveRegion={erro ? "polite" : undefined}
        className="mt-1 min-h-[16px] text-xs text-red-600"
      >
        {erro ?? ""}
      </Text>
    </View>
  );
}

// ---------------------------------------------------------------- Checkbox
/**
 * RF-47: toque simples para declarações opcionais do cadastro ("sou PCD").
 * Mesma linguagem visual do Campo (mb-4, label 13px semibold). Nativo ganha
 * feedback de pressão; web usa hover/outline — `active:opacity` não existe
 * no nativo e `opacity-0` de animação envenenaria a web (QA_UI_UX §1).
 */
export function Checkbox({
  checked,
  onPress,
  label,
  hint,
}: {
  checked: boolean;
  onPress: () => void;
  label: string;
  hint?: string;
}) {
  return (
    <View className="mb-4">
      <Pressable
        onPress={onPress}
        accessibilityRole="checkbox"
        accessibilityState={{ checked, disabled: false }}
        accessibilityLabel={label}
        accessibilityHint={hint}
        hitSlop={4}
        {...(Platform.OS === "web" ? { "aria-checked": checked } : {})}
        className={`flex-row items-center rounded-xl border-2 px-3.5 py-3 transition-colors active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 motion-reduce:transform-none motion-reduce:transition-none ${
          checked ? "border-blue-500 bg-blue-50" : "border-slate-200 bg-slate-50"
        }`}
      >
        <View
          className={`mr-3 h-[22px] w-[22px] items-center justify-center rounded-md border-2 ${
            checked ? "border-blue-600 bg-blue-600" : "border-slate-300 bg-white"
          }`}
        >
          {checked ? (
            <Ionicons name="checkmark" size={15} color="#fff" />
          ) : null}
        </View>
        <Text className="flex-1 text-[14px] font-semibold text-slate-800">
          {label}
        </Text>
      </Pressable>
      {hint ? (
        <Text className="mt-1 text-[11px] leading-4 text-slate-600">{hint}</Text>
      ) : null}
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
            accessibilityRole="button"
            accessibilityLabel={`${andar}º andar`}
            accessibilityHint="Filtra o mapa de vagas por andar"
            accessibilityState={{ selected: ativo, disabled: false }}
            hitSlop={6}
            {...(Platform.OS === "web" ? { "aria-pressed": ativo } : {})}
            className={`rounded-full border px-4 py-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 motion-reduce:transition-none ${
              ativo
                ? "border-blue-600 bg-blue-600"
                : "border-slate-200 bg-white hover:bg-blue-50 active:bg-blue-100"
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
          <Text className="text-xs text-slate-600">{i.rotulo}</Text>
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
      <Text className="text-sm text-slate-600">{label}</Text>
    </View>
  );
}

/**
 * Ícone de estado 100% vetorial (Ionicons + badge desenhado). Substitui os
 * emojis/Unicode que viravam "tofu" (▯) quando a fonte de símbolos não
 * existia no navegador/aparelho. Lei da similaridade: todos os estados
 * vazios/erro usam o mesmo badge, mudando apenas cor e pictograma.
 */
export function IconeEstado({
  nome = "car-outline",
  tom = "azul",
  tamanho = 48,
}: {
  nome?: ComponentProps<typeof Ionicons>["name"];
  tom?: "azul" | "ambar" | "vermelho" | "neutro";
  tamanho?: number;
}) {
  const paleta = {
    azul: { bg: "#EFF6FF", borda: "#BFDBFE", fg: "#2563EB" },
    ambar: { bg: "#FFFBEB", borda: "#FCD34D", fg: "#B45309" },
    vermelho: { bg: "#FEF2F2", borda: "#FCA5A5", fg: "#B91C1C" },
    neutro: { bg: "#F1F5F9", borda: "#CBD5E1", fg: "#475569" },
  }[tom];
  return (
    <View
      accessibilityRole="image"
      className="items-center justify-center rounded-2xl border"
      style={{
        width: tamanho,
        height: tamanho,
        backgroundColor: paleta.bg,
        borderColor: paleta.borda,
      }}
    >
      <Ionicons name={nome} size={Math.round(tamanho * 0.5)} color={paleta.fg} />
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
      <IconeEstado nome="warning-outline" tom="ambar" />
      <Text className="text-base font-bold text-slate-900">{titulo}</Text>
      {descricao ? (
        <Text className="text-center text-sm text-slate-600">{descricao}</Text>
      ) : null}
      {onAcao ? <Botao label={acaoLabel} onPress={onAcao} variant="contorno" /> : null}
    </Card>
  );
}

export function BlocoVazio({
  nomeIcone = "car-outline",
  tomIcone = "azul",
  titulo,
  descricao,
  acaoLabel,
  onAcao,
}: {
  nomeIcone?: ComponentProps<typeof Ionicons>["name"];
  tomIcone?: "azul" | "ambar" | "vermelho" | "neutro";
  titulo: string;
  descricao?: string;
  acaoLabel?: string;
  onAcao?: () => void;
}) {
  return (
    <Card className="items-center gap-3 p-8">
      <IconeEstado nome={nomeIcone} tom={tomIcone} />
      <Text className="text-base font-bold text-slate-900">{titulo}</Text>
      {descricao ? (
        <Text className="text-center text-sm text-slate-600">{descricao}</Text>
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

// ---------------------------------------------------------------- Esqueleto do mapa
/** Estado de carregamento com conteúdo: o spinner isolado no meio de uma área
    branca parecia "tela quebrada" no celular. */
export function EsqueletoMapa() {
  return (
    <View
      accessibilityRole="progressbar"
      accessibilityLabel="Carregando mapa de vagas"
      className="items-center py-10"
    >
      <ActivityIndicator size="large" color={colors.primary} />
      <Text className="mt-4 text-sm font-medium text-slate-600">
        Carregando mapa de vagas…
      </Text>
      <View className="mt-6 w-full flex-row flex-wrap justify-center gap-2">
        {Array.from({ length: 8 }).map((_, indice) => (
          <View
            key={indice}
            className="rounded-xl border border-slate-200 bg-slate-100"
            style={{ width: 56, height: 44 }}
          />
        ))}
      </View>
    </View>
  );
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
  const { height } = useWindowDimensions();
  const surg = useRef(new Animated.Value(0)).current;
  const reduzido = useMovimentoReduzido();
  useEffect(() => {
    if (visivel) {
      if (reduzido) {
        surg.setValue(1);
        return;
      }
      surg.setValue(0);
      Animated.timing(surg, {
        toValue: 1,
        duration: 170,
        easing: Easing.out(Easing.quad),
        useNativeDriver: Platform.OS !== "web",
      }).start();
    }
  }, [visivel, surg, reduzido]);
  return (
    <Modal
      visible={visivel}
      transparent
      animationType={reduzido ? "none" : "fade"}
      onRequestClose={aoFechar}
      statusBarTranslucent
      accessibilityViewIsModal
      accessibilityLabel={titulo}
    >
      <KeyboardAvoidingView
        className="flex-1"
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 24}
      >
      <View className="flex-1 items-center justify-center bg-black/50 p-4">
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Fechar formulário"
          accessibilityHint="Toque fora do cartão para cancelar"
          onPress={aoFechar}
          className="absolute inset-0"
        />
        <Animated.View
          style={{
            width: "100%",
            maxWidth: 448,
            maxHeight: Math.round(height * 0.88),
            opacity: surg,
            transform: [
              { scale: surg.interpolate({ inputRange: [0, 1], outputRange: [0.95, 1] }) },
            ],
          }}
        >
          <Card className="min-w-0 overflow-hidden p-5">
            <Text className="text-lg font-extrabold text-slate-900">{titulo}</Text>
            {descricao ? (
              <Text className="mt-0.5 text-[13px] text-slate-600">{descricao}</Text>
            ) : null}
            <ScrollView
              style={{ maxHeight: 420 }}
              className="mt-4"
              keyboardShouldPersistTaps="handled"
              contentContainerStyle={{ paddingBottom: 16 }}
            >
              {children}
            </ScrollView>
            <View className="mt-5 flex-row flex-wrap gap-2">
              <Botao
                label="Cancelar"
                variant="contorno"
                onPress={aoFechar}
                className="min-w-0 basis-[120px] flex-grow flex-shrink"
              />
              <Botao
                label={rotuloConfirmar}
                onPress={aoConfirmar}
                loading={ocupado}
                className="min-w-0 basis-[120px] flex-grow flex-shrink"
              />
            </View>
          </Card>
        </Animated.View>
      </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}
