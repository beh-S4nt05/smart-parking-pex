import { linkNav, minW0Flex1 } from "../styles/recipes";
import { Alert, Linking, Platform, Pressable, Text, View } from "react-native";
import { Link, useRouter } from "expo-router";
import { useAuth } from "../hooks/useAuth";
import { API_URL } from "../services/api";
import { Botao, LogoBlox, Logo } from "./ui";

/**
 * Cabeçalho público unificado em gradiente de marca.
 *
 * Dois arranjos puramente CSS (sem medir a janela em JS, para não gerar
 * salto de layout nem React #418 na hidratação):
 *   · ≥ lg: navegação completa em linha;
 *   · < lg: navegação visível em segunda linha, dentro do fluxo.
 *
 * Lei de Jakob: o mesmo lockup, a mesma ordem e os mesmos rótulos em TODAS
 * as rotas. Lei da semelhança: todos os links usam o mesmo formato de pill.
 * Von Restorff: somente o link ativo e a ação de entrada recebem cor cheia.
 *
 * Os itens de navegação são UM único <Link>: envolver um Pressable com
 * accessibilityRole="link" dentro de outro <Link> duplicava o papel na
 * árvore de acessibilidade (dois "links" com o mesmo nome).
 */
const LINKS = [
  { label: "Início", href: "/" },
  { label: "Explorar shoppings", href: "/explorar" },
] as const;

const CLASSE_LINK = linkNav;

export default function Header({ rotaAtual = "/" }: { rotaAtual?: string }) {
  const router = useRouter();
  const { user, isAuthenticated, canAccessPanel, signOut } = useAuth();

  const abrirAjuda = () =>
    Alert.alert(
      "HelpDesk Smart Parking",
      "Documentação da API em /docs · (92) 98123-0258\nbehsolutionsandautomations@gmail.com",
      Platform.OS === "web"
        ? [
            { text: "Fechar", style: "cancel" },
            {
              text: "Abrir /docs",
              onPress: () => Linking.openURL(`${API_URL}/docs`),
            },
          ]
        : [{ text: "Fechar" }],
    );

  const links = () =>
    LINKS.map((l) => {
      const ativo = rotaAtual === l.href;
      return (
        <Link
          key={l.label}
          href={l.href as never}
          accessibilityRole="link"
          accessibilityLabel={l.label}
          accessibilityState={{ selected: ativo }}
          className={`${CLASSE_LINK} ${ativo ? "bg-blue-600" : ""}`}
        >
          <Text
            className={`text-sm font-semibold content-center items-center ${
              ativo ? "text-white" : "text-slate-100"
            }`}
          >
            {l.label}
          </Text>
        </Link>
      );
    });

  const ajuda = () => (
    <Pressable
      onPress={abrirAjuda}
      accessibilityRole="button"
      accessibilityLabel="Abrir ajuda do HelpDesk"
      hitSlop={4}
      className="min-h-11 min-w-0 flex-row items-center content-center rounded-lg px-2 py-2 text-blue-200 web:transition-colors hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 web:motion-reduce:transition-none sm:px-3"
    >
      <Text className="text-sm font-semibold text-blue-200">Ajuda</Text>
    </Pressable>
  );

  return (
    <View className="sp-header">
      <View className="mx-auto w-full max-w-7xl flex-row items-center justify-between gap-2 px-3 py-3 sm:gap-3 sm:px-6 3xl:px-8 3xl:py-4">
        <Link
          href="/"
          accessibilityRole="link"
          accessibilityLabel="Ir para a página inicial"
          className="min-h-11 min-w-11 flex-row items-center justify-center"
        >
          <View className="sm:hidden">
            <Logo size={40} tone="white" />
          </View>
          <View className="hidden sm:flex">
            <LogoBlox claro />
          </View>
        </Link>

        <View className="hidden min-w-0 flex-1 flex-row items-center justify-center gap-1 lg:flex">
          {links()}
          {ajuda()}
        </View>

        <View className="min-w-0 flex-row items-center gap-1 sm:gap-2">
          {isAuthenticated ? (
            <>
              <Text numberOfLines={1} className="hidden max-w-40 text-sm font-semibold text-slate-100 lg:flex 3xl:max-w-48">
                {user?.nome}
              </Text>
              <Link
                href={canAccessPanel ? "/dashboard" : "/reservas"}
                accessibilityRole="link"
                accessibilityLabel={canAccessPanel ? "Abrir painel administrativo" : "Minhas reservas"}
                className="min-h-11 flex-row items-center justify-center rounded-lg bg-blue-600 px-3 web:transition-colors hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 sm:px-4"
              >
                <Text className="text-sm font-semibold text-white">{canAccessPanel ? "Painel" : "Minhas reservas"}</Text>
              </Link>
              <Link
                href="/perfil"
                accessibilityRole="link"
                accessibilityLabel="Minha conta"
                className="hidden min-h-11 flex-row items-center justify-center rounded-lg px-3 text-slate-100 web:transition-colors hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 sm:flex"
              >
                <Text className="text-sm font-semibold text-slate-100">Conta</Text>
              </Link>
              <Pressable
                onPress={() => signOut()}
                accessibilityRole="button"
                accessibilityLabel="Encerrar sessão"
                className="hidden min-h-11 flex-row items-center justify-center rounded-lg px-3 text-slate-100 web:transition-colors hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 sm:flex"
              >
                <Text className="text-sm font-medium text-slate-200">Sair</Text>
              </Pressable>
            </>
          ) : (
            <Botao label="Entrar" onPress={() => router.push("/login")} className="rounded-lg px-5 py-2" />
          )}
        </View>
      </View>

      <View className="sp-header-divisor border-t border-white/10 px-1 py-1 sm:px-4 lg:hidden 3xl:px-8">
        <View className="mx-auto w-full max-w-7xl flex-row flex-wrap items-center justify-between gap-x-2 gap-y-1">
          <View className="min-w-0 flex-row flex-wrap items-center gap-1">
            {links()}
            {ajuda()}
          </View>
          {isAuthenticated ? (
            <View className="flex-row items-center sm:hidden">
              <Link
                href="/perfil"
                accessibilityRole="link"
                accessibilityLabel="Minha conta"
                className="min-h-11 min-w-11 flex-row items-center justify-center rounded-lg px-2 text-slate-100 web:transition-colors hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300"
              >
                <Text className="text-sm font-semibold text-slate-100">Conta</Text>
              </Link>
              <Pressable
                onPress={() => signOut()}
                accessibilityRole="button"
                accessibilityLabel="Encerrar sessão"
                className="min-h-11 min-w-11 flex-row items-center justify-center rounded-lg px-2 text-slate-100 web:transition-colors hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300"
              >
                <Text className="text-sm font-medium text-slate-200">Sair</Text>
              </Pressable>
            </View>
          ) : null}
        </View>
      </View>
    </View>
  );
}

/** barra superior escura usada no Mapa (mobile) e no Simulador */
export function BarraEscura({
  titulo,
  subtitulo,
  aoVivo,
  voltar,
  direita,
}: {
  titulo: string;
  subtitulo?: string;
  aoVivo?: boolean;
  voltar?: React.ReactNode;
  direita?: React.ReactNode;
}) {
  return (
    <View className="sp-barra px-4 py-4 sm:px-6 3xl:py-5">
      <View className="mx-auto flex w-full max-w-7xl flex-row items-center gap-3">
        {voltar}
        <View className={minW0Flex1}>
          <Text className="text-lg font-bold text-white">{titulo}</Text>
          {subtitulo ? (
            <Text className="mt-0.5 text-xs text-slate-300">{subtitulo}</Text>
          ) : null}
        </View>
        {aoVivo ? (
          <View className="flex-row items-center gap-1.5">
            <View className="h-2 w-2 rounded-full bg-emerald-400" />
          </View>
        ) : null}
        {direita}
      </View>
    </View>
  );
}

export { Logo };
